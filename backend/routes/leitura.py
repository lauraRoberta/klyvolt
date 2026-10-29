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

@router.get("/{id_leitura}", response_model=schemas.LeituraResponse)
def buscar_leitura(id_leitura: int, db: Session = Depends(get_db)):
    leitura = db.get(models.Leitura, id_leitura)
    if leitura is None:
        raise HTTPException(status_code=404, detail="Leitura não encontrada.")
    return leitura
 
 
@router.put("/{id_leitura}", response_model=schemas.LeituraResponse)
def atualizar_leitura(id_leitura: int, dados: schemas.LeituraCreate, db: Session = Depends(get_db)):
    leitura = db.get(models.Leitura, id_leitura)
    if leitura is None:
        raise HTTPException(status_code=404, detail="Leitura não encontrada.")
    valores = dados.model_dump()
    # data_leitura é obrigatória no banco: se não vier, mantém a data que já está salva.
    if valores.get("data_leitura") is None:
        valores.pop("data_leitura", None)
    for campo, valor in valores.items():
        setattr(leitura, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="O sensor, o usuário ou o consumo informado não existe.")
    db.refresh(leitura)
    return leitura
 
 
@router.delete("/{id_leitura}", status_code=204)
def excluir_leitura(id_leitura: int, db: Session = Depends(get_db)):
    leitura = db.get(models.Leitura, id_leitura)
    if leitura is None:
        raise HTTPException(status_code=404, detail="Leitura não encontrada.")
    db.delete(leitura)  # tomadas de decisão ligadas a ela ficam sem leitura (SET NULL)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível excluir a leitura.")
    return Response(status_code=204)
 