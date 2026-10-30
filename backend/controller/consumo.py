"""Rotas de CONSUMO (CRUD) e cálculo pelo período.

Consumo do período (kWh) = soma das leituras dos sensores da máquina no período.
Custo estimado (R$) = consumo (kWh) × tarifa da empresa (R$/kWh).
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from database import executar, um_registro
from models.consumo import CalculoConsumoResponse, ConsumoCreate, ConsumoResponse
from seguranca import Contexto, exigir_operador, usuario_atual

router = APIRouter(prefix="/consumos", tags=["Consumo"])

COLUNAS = "id_consumo,data_inicio,data_fim,consumo_kwh,id_maquina"
DUPLICADO = "Já existe um consumo desta máquina para esse mesmo período."


def completar(contexto: Contexto, consumos: list[dict]) -> list[dict]:
    """Acrescenta máquina, duração, média por hora, custo e as leituras agregadas."""
    if not consumos:
        return consumos
    maquinas = {m["id_maquina"]: m["nome_maquina"] for m in executar(contexto.db.table("maquina").select("id_maquina,nome_maquina"))}
    ids = [c["id_consumo"] for c in consumos]
    agregadas: dict[int, list[float]] = {}
    for l in executar(contexto.db.table("leitura").select("id_consumo,valor_medido_kwh,data_leitura")
                      .in_("id_consumo", ids).order("data_leitura")):
        agregadas.setdefault(l["id_consumo"], []).append(float(l["valor_medido_kwh"]))
    resultado = []
    for c in consumos:
        inicio, fim = datetime.fromisoformat(c["data_inicio"]), datetime.fromisoformat(c["data_fim"])
        horas = (fim - inicio).total_seconds() / 3600
        kwh = float(c["consumo_kwh"])
        valores = agregadas.get(c["id_consumo"], [])
        resultado.append({
            **c, "nome_maquina": maquinas.get(c["id_maquina"]),
            "duracao_h": round(horas, 2), "media_kwh_h": round(kwh / horas, 2) if horas > 0 else None,
            "custo_estimado": round(kwh * contexto.tarifa_kwh, 2) if contexto.tarifa_kwh is not None else None,
            "leituras_agregadas": len(valores), "valores_leituras": valores,
        })
    return resultado


def decisoes_do_consumo(contexto: Contexto, id_consumo: int) -> list[str]:
    tomadas = executar(contexto.db.table("tomada_decisao").select("id_decisao,valor_referencia").eq("id_consumo", id_consumo))
    if not tomadas:
        return []
    regras = executar(contexto.db.table("decisao").select("nome_decisao").in_("id_decisao", [t["id_decisao"] for t in tomadas]))
    return sorted({r["nome_decisao"] for r in regras})


@router.get("", response_model=list[ConsumoResponse], summary="Listar consumos (mais recentes primeiro)")
def listar_consumos(id_maquina: int | None = Query(default=None),
                    inicio: datetime | None = Query(default=None), fim: datetime | None = Query(default=None),
                    contexto: Contexto = Depends(usuario_atual)):
    consulta = contexto.db.table("consumo").select(COLUNAS).order("data_inicio", desc=True)
    if id_maquina is not None:
        consulta = consulta.eq("id_maquina", id_maquina)
    if inicio is not None:
        consulta = consulta.gte("data_inicio", inicio.isoformat())
    if fim is not None:
        consulta = consulta.lte("data_inicio", fim.isoformat())
    return completar(contexto, executar(consulta))


@router.get("/calcular", response_model=CalculoConsumoResponse,
            summary="Calcular consumo de uma máquina pelo período (soma das leituras)")
def calcular_consumo(id_maquina: int = Query(gt=0), inicio: datetime = Query(), fim: datetime = Query(),
                     contexto: Contexto = Depends(usuario_atual)):
    if fim <= inicio:
        raise HTTPException(status_code=422, detail="A data final deve ser posterior à data inicial.")
    um_registro(executar(contexto.db.table("maquina").select("id_maquina").eq("id_maquina", id_maquina)), "Máquina")
    linhas = executar(contexto.db.rpc("kv_calcular_consumo",
                                      {"p_id_maquina": id_maquina, "p_inicio": inicio.isoformat(), "p_fim": fim.isoformat()}))
    linha = linhas[0] if linhas else {"total_kwh": 0, "leituras": 0}
    return {"id_maquina": id_maquina, "data_inicio": inicio, "data_fim": fim,
            "total_kwh": float(linha["total_kwh"]), "leituras": int(linha["leituras"])}


@router.get("/{id_consumo}", response_model=ConsumoResponse, summary="Consultar consumo por ID")
def buscar_consumo(id_consumo: int, contexto: Contexto = Depends(usuario_atual)):
    consumo = um_registro(executar(contexto.db.table("consumo").select(COLUNAS).eq("id_consumo", id_consumo)), "Consumo")
    return completar(contexto, [consumo])[0]


@router.post("", response_model=ConsumoResponse, status_code=status.HTTP_201_CREATED, summary="Registrar consumo")
def criar_consumo(consumo: ConsumoCreate, contexto: Contexto = Depends(exigir_operador)):
    linhas = executar(contexto.db.table("consumo").insert(consumo.model_dump(mode="json")).select(COLUNAS), duplicado=DUPLICADO)
    novo = completar(contexto, linhas)[0]
    return {**novo, "decisoes_acionadas": decisoes_do_consumo(contexto, novo["id_consumo"])}


@router.put("/{id_consumo}", response_model=ConsumoResponse, summary="Atualizar consumo")
def atualizar_consumo(id_consumo: int, consumo: ConsumoCreate, contexto: Contexto = Depends(exigir_operador)):
    linhas = executar(contexto.db.table("consumo").update(consumo.model_dump(mode="json")).eq("id_consumo", id_consumo)
                      .select(COLUNAS), duplicado=DUPLICADO)
    atual = completar(contexto, [um_registro(linhas, "Consumo")])[0]
    return {**atual, "decisoes_acionadas": decisoes_do_consumo(contexto, id_consumo)}


@router.delete("/{id_consumo}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Excluir consumo (as leituras voltam a ficar pendentes)")
def excluir_consumo(id_consumo: int, contexto: Contexto = Depends(exigir_operador)):
    um_registro(executar(contexto.db.table("consumo").delete().eq("id_consumo", id_consumo).select("id_consumo")), "Consumo")
    return None
