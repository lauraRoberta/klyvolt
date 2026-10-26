from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db

router = APIRouter(
    prefix="/sensores",
    tags=["Sensor"]
)


@router.post(
    "",
    response_model=schemas.SensorResponse
)
def criar_sensor(
    sensor: schemas.SensorCreate,
    db: Session = Depends(get_db)
):
    # Antes de inserir, confere se a máquina informada existe
    maquina = (
        db.query(models.Maquina)
        .filter(models.Maquina.id_maquina == sensor.id_maquina)
        .first()
    )

    if maquina is None:
        raise HTTPException(
            status_code=404,
            detail="Máquina não encontrada"
        )

    novo_sensor = models.Sensor(
        numero_serie=sensor.numero_serie,
        fabricante=sensor.fabricante,
        modelo=sensor.modelo,
        tipo_sensor=sensor.tipo_sensor,
        unidade_medida=sensor.unidade_medida,
        protocolo_comunicacao=sensor.protocolo_comunicacao,
        mac_address=sensor.mac_address,
        endereco_ip=sensor.endereco_ip,
        token_autenticacao=sensor.token_autenticacao,
        status_conexao=sensor.status_conexao,
        data_instalacao=sensor.data_instalacao,
        data_ultima_calibracao=sensor.data_ultima_calibracao,
        status=sensor.status,
        id_maquina=sensor.id_maquina
    )

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


@router.get(
    "",
    response_model=list[schemas.SensorResponse]
)
def listar_sensores(
    db: Session = Depends(get_db)
):
    return db.query(models.Sensor).all()