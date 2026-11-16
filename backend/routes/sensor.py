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


def buscar_sensor_ou_404(db: Session, id_sensor: int) -> models.Sensor:
    obj = db.get(models.Sensor, id_sensor)
    if obj is None:
        raise HTTPException(status_code=404, detail="Sensor não encontrado(a)")
    return obj
 
 
@router.get("/{id_sensor}", response_model=schemas.SensorResponse)
def obter_sensor(id_sensor: int, db: Session = Depends(get_db)):
    return buscar_sensor_ou_404(db, id_sensor)
 
 
@router.put("/{id_sensor}", response_model=schemas.SensorResponse)
def atualizar_sensor(id_sensor: int, dados: schemas.SensorCreate, db: Session = Depends(get_db)):
    obj = buscar_sensor_ou_404(db, id_sensor)
    for campo, valor in dados.model_dump().items():
        if campo == "token_autenticacao" and valor is None:
            continue  # o front não recebe o token, então não pode apagá-lo
        setattr(obj, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Valor duplicado ou referência inexistente")
    db.refresh(obj)
    return obj
 
 
@router.delete("/{id_sensor}", status_code=204)
def remover_sensor(id_sensor: int, db: Session = Depends(get_db)):
    obj = buscar_sensor_ou_404(db, id_sensor)
    try:
        db.delete(obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não pode ser removido: há registros que dependem dele")
 