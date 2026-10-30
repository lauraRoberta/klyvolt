"""Rotas de TOMADA_DECISAO (acionamentos das regras).

Os acionamentos são criados automaticamente pelo banco. A equipe consulta e
registra o resultado (executada, cancelada ou falha). Não existe integração
com equipamentos: nenhuma máquina é desligada automaticamente pelo sistema.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Query

from database import executar, um_registro
from models.tomada_decisao import TomadaDecisaoResponse, TomadaDecisaoUpdate
from seguranca import Contexto, exigir_operador, usuario_atual

router = APIRouter(prefix="/tomadas-decisao", tags=["Tomada de Decisão"])

COLUNAS = "id_tomada_decisao,data_tomada_decisao,valor_referencia,status_execucao,observacao,id_decisao,id_leitura,id_consumo"


def completar(contexto: Contexto, tomadas: list[dict]) -> list[dict]:
    if not tomadas:
        return tomadas
    nomes = {r["id_decisao"]: r["nome_decisao"] for r in executar(contexto.db.table("decisao").select("id_decisao,nome_decisao"))}
    return [{**t, "nome_decisao": nomes.get(t["id_decisao"])} for t in tomadas]


@router.get("", response_model=list[TomadaDecisaoResponse], summary="Listar acionamentos (mais recentes primeiro)")
def listar_tomadas(status_execucao: Literal["pendente", "executada", "cancelada", "falha"] | None = Query(default=None),
                   id_decisao: int | None = Query(default=None), limite: int = Query(default=200, ge=1, le=1000),
                   contexto: Contexto = Depends(usuario_atual)):
    consulta = contexto.db.table("tomada_decisao").select(COLUNAS).order("data_tomada_decisao", desc=True).limit(limite)
    if status_execucao:
        consulta = consulta.eq("status_execucao", status_execucao)
    if id_decisao is not None:
        consulta = consulta.eq("id_decisao", id_decisao)
    return completar(contexto, executar(consulta))


@router.get("/{id_tomada_decisao}", response_model=TomadaDecisaoResponse, summary="Consultar acionamento por ID")
def buscar_tomada(id_tomada_decisao: int, contexto: Contexto = Depends(usuario_atual)):
    linha = um_registro(executar(contexto.db.table("tomada_decisao").select(COLUNAS)
                                 .eq("id_tomada_decisao", id_tomada_decisao)), "Acionamento")
    return completar(contexto, [linha])[0]


@router.put("/{id_tomada_decisao}", response_model=TomadaDecisaoResponse, summary="Registrar o resultado do acionamento")
def atualizar_tomada(id_tomada_decisao: int, dados: TomadaDecisaoUpdate, contexto: Contexto = Depends(exigir_operador)):
    linhas = executar(contexto.db.table("tomada_decisao").update(dados.model_dump())
                      .eq("id_tomada_decisao", id_tomada_decisao).select(COLUNAS))
    return completar(contexto, [um_registro(linhas, "Acionamento")])[0]
