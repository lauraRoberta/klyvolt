from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db
from escopo import consulta_sensores, maquina_da_empresa, sensor_da_empresa
from seguranca import Sessao, sessao_atual

router = APIRouter(
    prefix="/sensores",
    tags=["Sensor"]
)


@router.post("", response_model=schemas.SensorResponse)
def criar_sensor(
    sensor: schemas.SensorCreate,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    # A máquina precisa existir e ser da empresa de quem está logado
    maquina_da_empresa(db, sensor.id_maquina, sessao.id_empresa)

    novo_sensor = models.Sensor(**sensor.model_dump())
    db.add(novo_sensor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Número de série, MAC address ou token já cadastrado"
        )

    db.refresh(novo_sensor)
    return novo_sensor


@router.get("", response_model=list[schemas.SensorResponse])
def listar_sensores(
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    return consulta_sensores(db, sessao.id_empresa).all()


@router.get("/{id_sensor}", response_model=schemas.SensorResponse)
def obter_sensor(
    id_sensor: int,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    return sensor_da_empresa(db, id_sensor, sessao.id_empresa)


@router.put("/{id_sensor}", response_model=schemas.SensorResponse)
def atualizar_sensor(
    id_sensor: int,
    dados: schemas.SensorCreate,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    obj = sensor_da_empresa(db, id_sensor, sessao.id_empresa)
    maquina_da_empresa(db, dados.id_maquina, sessao.id_empresa)
    for campo, valor in dados.model_dump().items():
        if campo == "token_autenticacao" and valor is None:
            continue  # sem token novo, mantém o que já está salvo
        setattr(obj, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Valor duplicado ou referência inexistente")
    db.refresh(obj)
    return obj


@router.delete("/{id_sensor}", status_code=204)
def remover_sensor(
    id_sensor: int,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    obj = sensor_da_empresa(db, id_sensor, sessao.id_empresa)
    try:
        db.delete(obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não pode ser removido: há registros que dependem dele")