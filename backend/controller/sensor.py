"""Rotas de SENSOR (CRUD), com resumo das leituras de cada sensor.

O token de autenticação do sensor é gravado, mas nunca é devolvido.
"""
from fastapi import APIRouter, Depends, status

from database import executar, um_registro
from models.sensor import SensorCreate, SensorResponse
from seguranca import Contexto, exigir_admin, usuario_atual

router = APIRouter(prefix="/sensores", tags=["Sensor"])

COLUNAS = ("id_sensor,numero_serie,fabricante,modelo,tipo_sensor,unidade_medida,protocolo_comunicacao,"
           "mac_address,endereco_ip,status_conexao,data_instalacao,data_ultima_calibracao,status,id_maquina")
DUPLICADO = "Número de série, endereço MAC ou token já cadastrado."


def completar(contexto: Contexto, sensores: list[dict]) -> list[dict]:
    """Acrescenta máquina, totais (kv_resumo_sensores) e as 12 leituras mais recentes."""
    if not sensores:
        return sensores
    maquinas = {m["id_maquina"]: m["nome_maquina"] for m in executar(contexto.db.table("maquina").select("id_maquina,nome_maquina"))}
    resumo = {r["id_sensor"]: r for r in executar(contexto.db.rpc("kv_resumo_sensores"))}
    ids = [s["id_sensor"] for s in sensores]
    recentes: dict[int, list] = {}
    leituras = executar(contexto.db.table("leitura").select("id_sensor,data_leitura,valor_medido_kwh")
                        .in_("id_sensor", ids).order("data_leitura", desc=True).limit(500))
    for l in leituras:
        lista = recentes.setdefault(l["id_sensor"], [])
        if len(lista) < 12:
            lista.insert(0, {"data_leitura": l["data_leitura"], "valor_medido_kwh": l["valor_medido_kwh"]})
    resultado = []
    for s in sensores:
        r = resumo.get(s["id_sensor"], {})
        resultado.append({
            **s, "nome_maquina": maquinas.get(s["id_maquina"]),
            "total_kwh": r.get("total_kwh", 0), "hoje_kwh": r.get("hoje_kwh", 0), "pico_kwh": r.get("pico_kwh", 0),
            "qtd_leituras": r.get("qtd_leituras", 0), "ultimas_leituras": recentes.get(s["id_sensor"], []),
        })
    return resultado


@router.get("", response_model=list[SensorResponse], summary="Listar sensores")
def listar_sensores(contexto: Contexto = Depends(usuario_atual)):
    return completar(contexto, executar(contexto.db.table("sensor").select(COLUNAS).order("numero_serie")))


@router.get("/{id_sensor}", response_model=SensorResponse, summary="Consultar sensor por ID")
def buscar_sensor(id_sensor: int, contexto: Contexto = Depends(usuario_atual)):
    sensor = um_registro(executar(contexto.db.table("sensor").select(COLUNAS).eq("id_sensor", id_sensor)), "Sensor")
    return completar(contexto, [sensor])[0]


@router.post("", response_model=SensorResponse, status_code=status.HTTP_201_CREATED, summary="Cadastrar sensor")
def criar_sensor(sensor: SensorCreate, contexto: Contexto = Depends(exigir_admin)):
    linhas = executar(contexto.db.table("sensor").insert(sensor.model_dump(mode="json")).select(COLUNAS), duplicado=DUPLICADO)
    return completar(contexto, linhas)[0]


@router.put("/{id_sensor}", response_model=SensorResponse, summary="Atualizar sensor (token vazio = mantém o atual)")
def atualizar_sensor(id_sensor: int, sensor: SensorCreate, contexto: Contexto = Depends(exigir_admin)):
    dados = sensor.model_dump(mode="json")
    if not dados.get("token_autenticacao"):
        dados.pop("token_autenticacao", None)
    linhas = executar(contexto.db.table("sensor").update(dados).eq("id_sensor", id_sensor).select(COLUNAS), duplicado=DUPLICADO)
    return completar(contexto, [um_registro(linhas, "Sensor")])[0]


@router.delete("/{id_sensor}", status_code=status.HTTP_204_NO_CONTENT, summary="Excluir sensor (e suas leituras)")
def excluir_sensor(id_sensor: int, contexto: Contexto = Depends(exigir_admin)):
    um_registro(executar(contexto.db.table("sensor").delete().eq("id_sensor", id_sensor).select("id_sensor")), "Sensor")
    return None
