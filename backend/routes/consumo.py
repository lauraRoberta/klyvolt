from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db
from escopo import consulta_consumos, consumo_da_empresa, maquina_da_empresa
from seguranca import Sessao, sessao_atual

router = APIRouter(
    prefix="/consumos",
    tags=["Consumo"]
)


@router.post("", response_model=schemas.ConsumoResponse)
def criar_consumo(
    consumo: schemas.ConsumoCreate,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    # A máquina precisa existir e ser da empresa de quem está logado
    maquina_da_empresa(db, consumo.id_maquina, sessao.id_empresa)

    novo_consumo = models.Consumo(
        data_inicio=consumo.data_inicio,
        data_fim=consumo.data_fim,
        consumo_kwh=consumo.consumo_kwh,
        id_maquina=consumo.id_maquina
    )

    db.add(novo_consumo)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe um consumo dessa máquina para esse período")

    db.refresh(novo_consumo)
    return novo_consumo


@router.get("", response_model=list[schemas.ConsumoResponse])
def listar_consumos(
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    return consulta_consumos(db, sessao.id_empresa).all()


@router.get("/{id_consumo}", response_model=schemas.ConsumoResponse)
def obter_consumo(
    id_consumo: int,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    return consumo_da_empresa(db, id_consumo, sessao.id_empresa)


@router.put("/{id_consumo}", response_model=schemas.ConsumoResponse)
def atualizar_consumo(
    id_consumo: int,
    dados: schemas.ConsumoCreate,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    obj = consumo_da_empresa(db, id_consumo, sessao.id_empresa)
    maquina_da_empresa(db, dados.id_maquina, sessao.id_empresa)
    for campo, valor in dados.model_dump().items():
        setattr(obj, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Valor duplicado ou referência inexistente")
    db.refresh(obj)
    return obj