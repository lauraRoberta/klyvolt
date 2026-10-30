"""Rotas de LEITURA (CRUD) e envio por sensor físico.

Cada leitura é a energia (kWh) medida em um intervalo. Ao gravar, o banco:
  • vincula a leitura ao consumo que cobre o horário (status "Agregada");
  • avalia as regras de decisão ativas e registra acionamentos.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from postgrest.exceptions import APIError

from database import cliente_publico, executar, traduzir_erro, um_registro
from models.leitura import LeituraCreate, LeituraResponse, LeituraSensorEntrada
from seguranca import Contexto, exigir_operador, usuario_atual

router = APIRouter(prefix="/leituras", tags=["Leitura"])

COLUNAS = "id_leitura,data_leitura,valor_medido_kwh,observacao_leitura,id_sensor,id_usuario,id_consumo"
DUPLICADO = "Já existe uma leitura deste sensor nesse mesmo horário."


def completar(contexto: Contexto, leituras: list[dict]) -> list[dict]:
    if not leituras:
        return leituras
    series = {s["id_sensor"]: s["numero_serie"] for s in executar(contexto.db.table("sensor").select("id_sensor,numero_serie"))}
    return [{**l, "numero_serie_sensor": series.get(l["id_sensor"])} for l in leituras]


def decisoes_da_leitura(contexto: Contexto, id_leitura: int) -> list[str]:
    tomadas = executar(contexto.db.table("tomada_decisao").select("id_decisao").eq("id_leitura", id_leitura))
    if not tomadas:
        return []
    regras = executar(contexto.db.table("decisao").select("nome_decisao").in_("id_decisao", [t["id_decisao"] for t in tomadas]))
    return [r["nome_decisao"] for r in regras]


def dados_para_banco(leitura: LeituraCreate) -> dict:
    dados = leitura.model_dump(mode="json")
    if dados["data_leitura"] is None:
        dados.pop("data_leitura")  # o banco usa o horário atual de Brasília
    return dados


@router.get("", response_model=list[LeituraResponse], summary="Listar leituras (mais recentes primeiro)")
def listar_leituras(
    response: Response,
    id_sensor: int | None = Query(default=None),
    inicio: datetime | None = Query(default=None, description="Data/hora inicial (AAAA-MM-DDTHH:MM)"),
    fim: datetime | None = Query(default=None, description="Data/hora final"),
    limite: int = Query(default=500, ge=1, le=2000),
    contexto: Contexto = Depends(usuario_atual),
):
    consulta = contexto.db.table("leitura").select(COLUNAS, count="exact").order("data_leitura", desc=True).limit(limite)
    if id_sensor is not None:
        consulta = consulta.eq("id_sensor", id_sensor)
    if inicio is not None:
        consulta = consulta.gte("data_leitura", inicio.isoformat())
    if fim is not None:
        consulta = consulta.lte("data_leitura", fim.isoformat())
    try:
        resultado = consulta.execute()
    except APIError as erro:
        raise traduzir_erro(erro) from erro
    response.headers["X-Total-Count"] = str(resultado.count if resultado.count is not None else len(resultado.data))
    return completar(contexto, resultado.data)


@router.get("/{id_leitura}", response_model=LeituraResponse, summary="Consultar leitura por ID")
def buscar_leitura(id_leitura: int, contexto: Contexto = Depends(usuario_atual)):
    leitura = um_registro(executar(contexto.db.table("leitura").select(COLUNAS).eq("id_leitura", id_leitura)), "Leitura")
    return completar(contexto, [leitura])[0]


@router.post("", response_model=LeituraResponse, status_code=status.HTTP_201_CREATED, summary="Registrar leitura")
def criar_leitura(leitura: LeituraCreate, contexto: Contexto = Depends(exigir_operador)):
    linhas = executar(contexto.db.table("leitura").insert(dados_para_banco(leitura)).select(COLUNAS), duplicado=DUPLICADO)
    nova = completar(contexto, linhas)[0]
    return {**nova, "decisoes_acionadas": decisoes_da_leitura(contexto, nova["id_leitura"])}


@router.put("/{id_leitura}", response_model=LeituraResponse, summary="Atualizar leitura")
def atualizar_leitura(id_leitura: int, leitura: LeituraCreate, contexto: Contexto = Depends(exigir_operador)):
    linhas = executar(contexto.db.table("leitura").update(dados_para_banco(leitura)).eq("id_leitura", id_leitura).select(COLUNAS),
                      duplicado=DUPLICADO)
    atual = completar(contexto, [um_registro(linhas, "Leitura")])[0]
    return {**atual, "decisoes_acionadas": decisoes_da_leitura(contexto, id_leitura)}


@router.delete("/{id_leitura}", status_code=status.HTTP_204_NO_CONTENT, summary="Excluir leitura")
def excluir_leitura(id_leitura: int, contexto: Contexto = Depends(exigir_operador)):
    um_registro(executar(contexto.db.table("leitura").delete().eq("id_leitura", id_leitura).select("id_leitura")), "Leitura")
    return None


@router.post("/sensor", status_code=status.HTTP_201_CREATED,
             summary="Envio por sensor físico (cabeçalho X-Sensor-Token, sem login de usuário)")
def leitura_do_sensor(dados: LeituraSensorEntrada, x_sensor_token: str = Header(..., min_length=8)):
    parametros = {
        "p_token": x_sensor_token,
        "p_valor_kwh": round(dados.valor_medido_kwh, 2),
        "p_data_leitura": dados.data_leitura.isoformat() if dados.data_leitura else None,
        "p_observacao": dados.observacao_leitura,
    }
    id_leitura = executar(cliente_publico().rpc("kv_registrar_leitura_sensor", parametros))
    if not id_leitura:
        raise HTTPException(status_code=502, detail="O Supabase não confirmou a gravação da leitura.")
    return {"id_leitura": id_leitura}
