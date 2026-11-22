from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db
from escopo import consulta_maquinas, maquina_da_empresa, setor_da_empresa
from seguranca import Sessao, sessao_atual

router = APIRouter(
    prefix="/maquinas",
    tags=["Máquina"]
)


@router.post("", response_model=schemas.MaquinaResponse)
def criar_maquina(
    maquina: schemas.MaquinaCreate,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    # O setor precisa existir e ser da empresa de quem está logado
    setor_da_empresa(db, maquina.id_setor, sessao.id_empresa)

    nova_maquina = models.Maquina(
        nome_maquina=maquina.nome_maquina,
        descricao_maquina=maquina.descricao_maquina,
        potencia_nominal=maquina.potencia_nominal,
        numero_serie=maquina.numero_serie,
        id_setor=maquina.id_setor
    )

    db.add(nova_maquina)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe uma máquina com esse número de série")

    db.refresh(nova_maquina)
    return nova_maquina


@router.get("", response_model=list[schemas.MaquinaResponse])
def listar_maquinas(
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    return consulta_maquinas(db, sessao.id_empresa).all()


@router.get("/{id_maquina}", response_model=schemas.MaquinaResponse)
def obter_maquina(
    id_maquina: int,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    return maquina_da_empresa(db, id_maquina, sessao.id_empresa)


@router.put("/{id_maquina}", response_model=schemas.MaquinaResponse)
def atualizar_maquina(
    id_maquina: int,
    dados: schemas.MaquinaCreate,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    obj = maquina_da_empresa(db, id_maquina, sessao.id_empresa)
    setor_da_empresa(db, dados.id_setor, sessao.id_empresa)
    for campo, valor in dados.model_dump().items():
        setattr(obj, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Valor duplicado ou referência inexistente")
    db.refresh(obj)
    return obj


@router.delete("/{id_maquina}", status_code=204)
def remover_maquina(
    id_maquina: int,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    obj = maquina_da_empresa(db, id_maquina, sessao.id_empresa)
    try:
        db.delete(obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não pode ser removido: há registros que dependem dele")