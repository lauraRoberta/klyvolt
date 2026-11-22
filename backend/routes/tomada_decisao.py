from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db
from escopo import (
    consulta_tomadas,
    consumo_da_empresa,
    decisao_da_empresa,
    leitura_da_empresa,
    tomada_da_empresa,
)
from seguranca import Sessao, sessao_atual

router = APIRouter(
    prefix="/tomadas-decisao",
    tags=["Tomada de Decisão"]
)


def validar_referencias(db: Session, dados: schemas.TomadaDecisaoCreate, id_empresa: int):
    """Decisão, leitura e consumo informados precisam ser da mesma empresa de quem está logado."""
    decisao = decisao_da_empresa(db, dados.id_decisao, id_empresa)

    if dados.id_leitura is not None:
        leitura_da_empresa(db, dados.id_leitura, id_empresa)

    if dados.id_consumo is not None:
        consumo_da_empresa(db, dados.id_consumo, id_empresa)

    return decisao


def montar_resposta(t: models.TomadaDecisao, nome_decisao: str) -> dict:
    return {
        "id_tomada_decisao": t.id_tomada_decisao,
        "data_tomada_decisao": t.data_tomada_decisao,
        "decisao": nome_decisao,
        "valor_referencia": t.valor_referencia,
        "status_execucao": t.status_execucao,
        "observacao": t.observacao,
        "id_leitura": t.id_leitura,
        "id_consumo": t.id_consumo
    }


@router.post("", response_model=schemas.TomadaDecisaoResponse)
def criar_tomada_decisao(
    tomada: schemas.TomadaDecisaoCreate,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    decisao = validar_referencias(db, tomada, sessao.id_empresa)

    nova_tomada = models.TomadaDecisao(
        id_decisao=tomada.id_decisao,
        valor_referencia=tomada.valor_referencia,
        status_execucao=tomada.status_execucao,
        observacao=tomada.observacao,
        id_leitura=tomada.id_leitura,
        id_consumo=tomada.id_consumo
    )

    db.add(nova_tomada)
    db.commit()
    db.refresh(nova_tomada)

    return montar_resposta(nova_tomada, decisao.nome_decisao)


@router.get("", response_model=list[schemas.TomadaDecisaoResponse])
def listar_tomadas_decisao(
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    tomadas = consulta_tomadas(db, sessao.id_empresa).all()
    return [montar_resposta(t, t.decisao.nome_decisao) for t in tomadas]


@router.get("/{id_tomada_decisao}", response_model=schemas.TomadaDecisaoResponse)
def obter_tomada_decisao(
    id_tomada_decisao: int,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    return tomada_da_empresa(db, id_tomada_decisao, sessao.id_empresa)


@router.put("/{id_tomada_decisao}", response_model=schemas.TomadaDecisaoResponse)
def atualizar_tomada_decisao(
    id_tomada_decisao: int,
    dados: schemas.TomadaDecisaoCreate,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    obj = tomada_da_empresa(db, id_tomada_decisao, sessao.id_empresa)
    validar_referencias(db, dados, sessao.id_empresa)
    for campo, valor in dados.model_dump().items():
        setattr(obj, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Valor duplicado ou referência inexistente")
    db.refresh(obj)
    return obj