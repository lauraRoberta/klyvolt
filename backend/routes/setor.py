from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db
from escopo import consulta_setores, setor_da_empresa, usuario_da_empresa
from seguranca import Sessao, sessao_atual

router = APIRouter(
    prefix="/setores",
    tags=["Setor"]
)


@router.post("", response_model=schemas.SetorResponse)
def criar_setor(
    setor: schemas.SetorCreate,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    # O responsável precisa existir e ser da mesma empresa de quem está logado
    usuario_da_empresa(db, setor.id_usuario_responsavel, sessao.id_empresa, "Usuário responsável")

    novo_setor = models.Setor(
        nome_setor=setor.nome_setor,
        divisao_setor=setor.divisao_setor,
        id_usuario_responsavel=setor.id_usuario_responsavel
    )

    db.add(novo_setor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe um setor com esse nome")

    db.refresh(novo_setor)
    return novo_setor


@router.get("", response_model=list[schemas.SetorResponse])
def listar_setores(
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    return consulta_setores(db, sessao.id_empresa).all()


@router.get("/{id_setor}", response_model=schemas.SetorResponse)
def obter_setor(
    id_setor: int,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    return setor_da_empresa(db, id_setor, sessao.id_empresa)


@router.put("/{id_setor}", response_model=schemas.SetorResponse)
def atualizar_setor(
    id_setor: int,
    dados: schemas.SetorCreate,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    obj = setor_da_empresa(db, id_setor, sessao.id_empresa)
    usuario_da_empresa(db, dados.id_usuario_responsavel, sessao.id_empresa, "Usuário responsável")
    for campo, valor in dados.model_dump().items():
        setattr(obj, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Valor duplicado ou referência inexistente")
    db.refresh(obj)
    return obj


@router.delete("/{id_setor}", status_code=204)
def remover_setor(
    id_setor: int,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    obj = setor_da_empresa(db, id_setor, sessao.id_empresa)
    try:
        db.delete(obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não pode ser removido: há registros que dependem dele")