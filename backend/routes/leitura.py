from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db

router = APIRouter(
    prefix="/leituras",
    tags=["Leitura"]
)


@router.post(
    "",
    response_model=schemas.LeituraResponse
)
def criar_leitura(
    leitura: schemas.LeituraCreate,
    db: Session = Depends(get_db)
):
    # O sensor é obrigatório e precisa existir
    sensor = (
        db.query(models.Sensor)
        .filter(models.Sensor.id_sensor == leitura.id_sensor)
        .first()
    )

    if sensor is None:
        raise HTTPException(
            status_code=404,
            detail="Sensor não encontrado"
        )

    # Usuário e consumo são opcionais, mas se vierem precisam existir
    if leitura.id_usuario is not None:
        usuario = (
            db.query(models.Usuario)
            .filter(models.Usuario.id_usuario == leitura.id_usuario)
            .first()
        )

        if usuario is None:
            raise HTTPException(
                status_code=404,
                detail="Usuário não encontrado"
            )

    if leitura.id_consumo is not None:
        consumo = (
            db.query(models.Consumo)
            .filter(models.Consumo.id_consumo == leitura.id_consumo)
            .first()
        )

        if consumo is None:
            raise HTTPException(
                status_code=404,
                detail="Consumo não encontrado"
            )

    nova_leitura = models.Leitura(
        valor_medido_kwh=leitura.valor_medido_kwh,
        observacao_leitura=leitura.observacao_leitura,
        id_sensor=leitura.id_sensor,
        id_usuario=leitura.id_usuario,
        id_consumo=leitura.id_consumo
    )

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


@router.get(
    "",
    response_model=list[schemas.LeituraResponse]
)
def listar_leituras(
    db: Session = Depends(get_db)
):
    return db.query(models.Leitura).all()


def buscar_leitura_ou_404(db: Session, id_leitura: int) -> models.Leitura:
    obj = db.get(models.Leitura, id_leitura)
    if obj is None:
        raise HTTPException(status_code=404, detail="Leitura não encontrado(a)")
    return obj
 
 
@router.get("/{id_leitura}", response_model=schemas.LeituraResponse)
def obter_leitura(id_leitura: int, db: Session = Depends(get_db)):
    return buscar_leitura_ou_404(db, id_leitura)
 
 
@router.put("/{id_leitura}", response_model=schemas.LeituraResponse)
def atualizar_leitura(id_leitura: int, dados: schemas.LeituraCreate, db: Session = Depends(get_db)):
    obj = buscar_leitura_ou_404(db, id_leitura)
    for campo, valor in dados.model_dump().items():
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