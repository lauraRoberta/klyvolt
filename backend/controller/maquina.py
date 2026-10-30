"""Rotas de MAQUINA (CRUD), com consumo registrado e custo estimado."""
from fastapi import APIRouter, Depends, Query, status

from database import executar, um_registro
from models.maquina import MaquinaCreate, MaquinaResponse
from seguranca import Contexto, exigir_admin, usuario_atual

router = APIRouter(prefix="/maquinas", tags=["Máquina"])

COLUNAS = "id_maquina,nome_maquina,descricao_maquina,potencia_nominal,numero_serie,id_setor"
DUPLICADO = "Já existe uma máquina com esse número de série."


def completar(contexto: Contexto, maquinas: list[dict]) -> list[dict]:
    """Acrescenta setor, quantidade de sensores, consumo total e custo (tarifa da empresa)."""
    if not maquinas:
        return maquinas
    setores = {s["id_setor"]: s["nome_setor"] for s in executar(contexto.db.table("setor").select("id_setor,nome_setor"))}
    sensores: dict[int, int] = {}
    for s in executar(contexto.db.table("sensor").select("id_maquina")):
        sensores[s["id_maquina"]] = sensores.get(s["id_maquina"], 0) + 1
    consumo: dict[int, float] = {}
    for c in executar(contexto.db.table("consumo").select("id_maquina,consumo_kwh")):
        consumo[c["id_maquina"]] = consumo.get(c["id_maquina"], 0) + float(c["consumo_kwh"])
    resultado = []
    for m in maquinas:
        kwh = consumo.get(m["id_maquina"])
        resultado.append({
            **m, "nome_setor": setores.get(m["id_setor"]), "qtd_sensores": sensores.get(m["id_maquina"], 0),
            "consumo_kwh": round(kwh, 2) if kwh is not None else None,
            "custo_estimado": round(kwh * contexto.tarifa_kwh, 2) if kwh is not None and contexto.tarifa_kwh is not None else None,
        })
    return resultado


@router.get("", response_model=list[MaquinaResponse], summary="Listar máquinas")
def listar_maquinas(id_setor: int | None = Query(default=None, description="Filtrar por setor"),
                    contexto: Contexto = Depends(usuario_atual)):
    consulta = contexto.db.table("maquina").select(COLUNAS).order("nome_maquina")
    if id_setor is not None:
        consulta = consulta.eq("id_setor", id_setor)
    return completar(contexto, executar(consulta))


@router.get("/{id_maquina}", response_model=MaquinaResponse, summary="Consultar máquina por ID")
def buscar_maquina(id_maquina: int, contexto: Contexto = Depends(usuario_atual)):
    maquina = um_registro(executar(contexto.db.table("maquina").select(COLUNAS).eq("id_maquina", id_maquina)), "Máquina")
    return completar(contexto, [maquina])[0]


@router.post("", response_model=MaquinaResponse, status_code=status.HTTP_201_CREATED, summary="Cadastrar máquina")
def criar_maquina(maquina: MaquinaCreate, contexto: Contexto = Depends(exigir_admin)):
    linhas = executar(contexto.db.table("maquina").insert(maquina.model_dump()).select(COLUNAS), duplicado=DUPLICADO)
    return completar(contexto, linhas)[0]


@router.put("/{id_maquina}", response_model=MaquinaResponse, summary="Atualizar máquina")
def atualizar_maquina(id_maquina: int, maquina: MaquinaCreate, contexto: Contexto = Depends(exigir_admin)):
    linhas = executar(contexto.db.table("maquina").update(maquina.model_dump()).eq("id_maquina", id_maquina).select(COLUNAS),
                      duplicado=DUPLICADO)
    return completar(contexto, [um_registro(linhas, "Máquina")])[0]


@router.delete("/{id_maquina}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Excluir máquina (e seus sensores, leituras e consumos)")
def excluir_maquina(id_maquina: int, contexto: Contexto = Depends(exigir_admin)):
    um_registro(executar(contexto.db.table("maquina").delete().eq("id_maquina", id_maquina).select("id_maquina")), "Máquina")
    return None
