from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db
from escopo import consulta_decisoes, decisao_da_empresa
from seguranca import Sessao, sessao_atual

router = APIRouter(
    prefix="/decisoes",
    tags=["Decisão"]
)


@router.post("", response_model=schemas.DecisaoResponse)
def criar_decisao(
    decisao: schemas.DecisaoCreate,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    nova_decisao = models.Decisao(
        id_empresa=sessao.id_empresa,
        nome_decisao=decisao.nome_decisao,
        descricao_decisao=decisao.descricao_decisao,
        criterio_acionado=decisao.criterio_acionado,
        operador=decisao.operador,
        limite_referencia=decisao.limite_referencia,
        unidade_limite=decisao.unidade_limite
    )

    db.add(nova_decisao)
    db.commit()
    db.refresh(nova_decisao)

    return nova_decisao


@router.get("", response_model=list[schemas.DecisaoResponse])
def listar_decisoes(
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    return consulta_decisoes(db, sessao.id_empresa).all()


@router.get("/{id_decisao}", response_model=schemas.DecisaoResponse)
def obter_decisao(
    id_decisao: int,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    return decisao_da_empresa(db, id_decisao, sessao.id_empresa)


@router.put("/{id_decisao}", response_model=schemas.DecisaoResponse)
def atualizar_decisao(
    id_decisao: int,
    dados: schemas.DecisaoCreate,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    obj = decisao_da_empresa(db, id_decisao, sessao.id_empresa)
    for campo, valor in dados.model_dump().items():
        setattr(obj, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Valor duplicado ou referência inexistente")
    db.refresh(obj)
    return obj


@router.delete("/{id_decisao}", status_code=204)
def remover_decisao(
    id_decisao: int,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    obj = decisao_da_empresa(db, id_decisao, sessao.id_empresa)
    try:
        db.delete(obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não pode ser removido: há registros que dependem dele")