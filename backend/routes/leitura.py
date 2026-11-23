from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db
from escopo import (
    consulta_leituras,
    consumo_da_empresa,
    leitura_da_empresa,
    sensor_da_empresa,
    usuario_da_empresa,
)
from seguranca import Sessao, sessao_atual

router = APIRouter(
    prefix="/leituras",
    tags=["Leitura"]
)


def validar_referencias(db: Session, leitura: schemas.LeituraCreate, id_empresa: int):
    """Sensor, usuário e consumo informados precisam ser da mesma empresa de quem está logado."""
    sensor_da_empresa(db, leitura.id_sensor, id_empresa)

    if leitura.id_usuario is not None:
        usuario_da_empresa(db, leitura.id_usuario, id_empresa)

    if leitura.id_consumo is not None:
        consumo_da_empresa(db, leitura.id_consumo, id_empresa)


@router.post("", response_model=schemas.LeituraResponse)
def criar_leitura(
    leitura: schemas.LeituraCreate,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    validar_referencias(db, leitura, sessao.id_empresa)

    dados = leitura.model_dump(exclude={"data_leitura"})
    nova_leitura = models.Leitura(**dados)

    # Se a data não vier, o banco usa o horário atual
    if leitura.data_leitura is not None:
        nova_leitura.data_leitura = leitura.data_leitura

    db.add(nova_leitura)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe uma leitura desse sensor nesse horário"
        )

    db.refresh(nova_leitura)
    return nova_leitura


@router.get("", response_model=list[schemas.LeituraResponse])
def listar_leituras(
    limite: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    # O sensor gera uma leitura a cada 10 s, então a lista traz só as mais recentes.
    return (
        consulta_leituras(db, sessao.id_empresa)
        .order_by(models.Leitura.data_leitura.desc())
        .limit(limite)
        .all()
    )


@router.get("/{id_leitura}", response_model=schemas.LeituraResponse)
def obter_leitura(
    id_leitura: int,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    return leitura_da_empresa(db, id_leitura, sessao.id_empresa)


@router.put("/{id_leitura}", response_model=schemas.LeituraResponse)
def atualizar_leitura(
    id_leitura: int,
    dados: schemas.LeituraCreate,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    obj = leitura_da_empresa(db, id_leitura, sessao.id_empresa)
    validar_referencias(db, dados, sessao.id_empresa)

    # Só atualiza os campos enviados, para não apagar dados do sensor sem querer
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        if campo == "data_leitura" and valor is None:
            continue  # coluna obrigatória: mantém a data atual
        setattr(obj, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Valor duplicado ou referência inexistente")
    db.refresh(obj)
    return obj