from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db

router = APIRouter(
    prefix="/consumos",
    tags=["Consumo"]
)


@router.post(
    "",
    response_model=schemas.ConsumoResponse
)
def criar_consumo(
    consumo: schemas.ConsumoCreate,
    db: Session = Depends(get_db)
):
    # Antes de inserir, confere se a máquina informada existe
    maquina = (
        db.query(models.Maquina)
        .filter(models.Maquina.id_maquina == consumo.id_maquina)
        .first()
    )

    if maquina is None:
        raise HTTPException(
            status_code=404,
            detail="Máquina não encontrada"
        )

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
        raise HTTPException(
            status_code=409,
            detail="Já existe um consumo dessa máquina para esse período"
        )

    db.refresh(novo_consumo)

    return novo_consumo


@router.get(
    "",
    response_model=list[schemas.ConsumoResponse]
)
def listar_consumos(
    db: Session = Depends(get_db)
):
    return db.query(models.Consumo).all()