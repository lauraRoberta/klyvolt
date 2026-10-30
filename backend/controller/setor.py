"""Rotas de SETOR (CRUD). A empresa do setor é sempre a do usuário logado."""
from fastapi import APIRouter, Depends, status

from database import executar, um_registro
from models.setor import SetorCreate, SetorResponse
from seguranca import Contexto, exigir_admin, usuario_atual

router = APIRouter(prefix="/setores", tags=["Setor"])

COLUNAS = "id_setor,nome_setor,divisao_setor,id_usuario_responsavel,id_empresa,ativo"
DUPLICADO = "Já existe um setor com esse nome na sua empresa."


def completar(contexto: Contexto, setores: list[dict]) -> list[dict]:
    """Acrescenta o nome do responsável e a quantidade de máquinas de cada setor."""
    if not setores:
        return setores
    usuarios = executar(contexto.db.table("usuario").select("id_usuario,nome_usuario"))
    nomes = {u["id_usuario"]: u["nome_usuario"] for u in usuarios}
    maquinas = executar(contexto.db.table("maquina").select("id_setor"))
    contagem: dict[int, int] = {}
    for m in maquinas:
        contagem[m["id_setor"]] = contagem.get(m["id_setor"], 0) + 1
    return [{**s, "nome_responsavel": nomes.get(s["id_usuario_responsavel"]),
             "qtd_maquinas": contagem.get(s["id_setor"], 0)} for s in setores]


@router.get("", response_model=list[SetorResponse], summary="Listar setores")
def listar_setores(contexto: Contexto = Depends(usuario_atual)):
    return completar(contexto, executar(contexto.db.table("setor").select(COLUNAS).order("nome_setor")))


@router.get("/{id_setor}", response_model=SetorResponse, summary="Consultar setor por ID")
def buscar_setor(id_setor: int, contexto: Contexto = Depends(usuario_atual)):
    setor = um_registro(executar(contexto.db.table("setor").select(COLUNAS).eq("id_setor", id_setor)), "Setor")
    return completar(contexto, [setor])[0]


@router.post("", response_model=SetorResponse, status_code=status.HTTP_201_CREATED, summary="Cadastrar setor")
def criar_setor(setor: SetorCreate, contexto: Contexto = Depends(exigir_admin)):
    linhas = executar(contexto.db.table("setor").insert(setor.model_dump()).select(COLUNAS), duplicado=DUPLICADO)
    return completar(contexto, linhas)[0]


@router.put("/{id_setor}", response_model=SetorResponse, summary="Atualizar setor")
def atualizar_setor(id_setor: int, setor: SetorCreate, contexto: Contexto = Depends(exigir_admin)):
    linhas = executar(contexto.db.table("setor").update(setor.model_dump()).eq("id_setor", id_setor).select(COLUNAS),
                      duplicado=DUPLICADO)
    return completar(contexto, [um_registro(linhas, "Setor")])[0]


@router.delete("/{id_setor}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Excluir setor (e, em cascata, suas máquinas, sensores, leituras e consumos)")
def excluir_setor(id_setor: int, contexto: Contexto = Depends(exigir_admin)):
    um_registro(executar(contexto.db.table("setor").delete().eq("id_setor", id_setor).select("id_setor")), "Setor")
    return None
