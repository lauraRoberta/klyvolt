"""Rotas de DECISAO (CRUD de regras).

Regras ativas são avaliadas pelo banco a cada nova leitura (critério
valor_medido_kwh) ou consumo (critério consumo_kwh). Quando a condição é
verdadeira, um acionamento é registrado em tomada_decisao.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from database import executar, um_registro
from models.decisao import DecisaoCreate, DecisaoResponse
from seguranca import Contexto, exigir_admin, usuario_atual

router = APIRouter(prefix="/decisoes", tags=["Decisão"])

COLUNAS = "id_decisao,nome_decisao,descricao_decisao,criterio_acionado,operador,limite_referencia,unidade_limite,ativo"
DUPLICADO = "Já existe uma regra com esse nome."


def completar(contexto: Contexto, regras: list[dict]) -> list[dict]:
    if not regras:
        return regras
    tomadas = executar(contexto.db.table("tomada_decisao").select("id_decisao,data_tomada_decisao")
                       .in_("id_decisao", [r["id_decisao"] for r in regras]).order("data_tomada_decisao", desc=True))
    contagem: dict[int, int] = {}
    ultimo: dict[int, str] = {}
    for t in tomadas:
        contagem[t["id_decisao"]] = contagem.get(t["id_decisao"], 0) + 1
        ultimo.setdefault(t["id_decisao"], t["data_tomada_decisao"])
    return [{**r, "acionamentos": contagem.get(r["id_decisao"], 0), "ultimo_acionamento": ultimo.get(r["id_decisao"])}
            for r in regras]


@router.get("", response_model=list[DecisaoResponse], summary="Listar regras de decisão")
def listar_decisoes(contexto: Contexto = Depends(usuario_atual)):
    return completar(contexto, executar(contexto.db.table("decisao").select(COLUNAS).order("nome_decisao")))


@router.get("/{id_decisao}", response_model=DecisaoResponse, summary="Consultar regra por ID")
def buscar_decisao(id_decisao: int, contexto: Contexto = Depends(usuario_atual)):
    regra = um_registro(executar(contexto.db.table("decisao").select(COLUNAS).eq("id_decisao", id_decisao)), "Regra")
    return completar(contexto, [regra])[0]


@router.post("", response_model=DecisaoResponse, status_code=status.HTTP_201_CREATED, summary="Cadastrar regra")
def criar_decisao(decisao: DecisaoCreate, contexto: Contexto = Depends(exigir_admin)):
    linhas = executar(contexto.db.table("decisao").insert(decisao.model_dump()).select(COLUNAS), duplicado=DUPLICADO)
    return completar(contexto, linhas)[0]


@router.put("/{id_decisao}", response_model=DecisaoResponse, summary="Atualizar regra")
def atualizar_decisao(id_decisao: int, decisao: DecisaoCreate, contexto: Contexto = Depends(exigir_admin)):
    linhas = executar(contexto.db.table("decisao").update(decisao.model_dump()).eq("id_decisao", id_decisao).select(COLUNAS),
                      duplicado=DUPLICADO)
    return completar(contexto, [um_registro(linhas, "Regra")])[0]


@router.delete("/{id_decisao}", status_code=status.HTTP_204_NO_CONTENT, summary="Excluir regra sem acionamentos")
def excluir_decisao(id_decisao: int, contexto: Contexto = Depends(exigir_admin)):
    regra = completar(contexto, [um_registro(executar(contexto.db.table("decisao").select(COLUNAS)
                                                      .eq("id_decisao", id_decisao)), "Regra")])[0]
    if regra["acionamentos"]:
        raise HTTPException(status_code=409, detail=(
            f"Esta regra possui {regra['acionamentos']} acionamento(s) no histórico e não pode ser excluída. "
            "Para interromper a avaliação, edite-a e marque como inativa."))
    executar(contexto.db.table("decisao").delete().eq("id_decisao", id_decisao).select("id_decisao"),
             vinculo="Esta regra possui acionamentos no histórico e não pode ser excluída.")
    return None
