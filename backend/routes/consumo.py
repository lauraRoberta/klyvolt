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


def buscar_consumo_ou_404(db: Session, id_consumo: int) -> models.Consumo:
    obj = db.get(models.Consumo, id_consumo)
    if obj is None:
        raise HTTPException(status_code=404, detail="Consumo não encontrado(a)")
    return obj
 
 
@router.get("/{id_consumo}", response_model=schemas.ConsumoResponse)
def obter_consumo(id_consumo: int, db: Session = Depends(get_db)):
    return buscar_consumo_ou_404(db, id_consumo)
 
 
@router.put("/{id_consumo}", response_model=schemas.ConsumoResponse)
def atualizar_consumo(id_consumo: int, dados: schemas.ConsumoCreate, db: Session = Depends(get_db)):
    obj = buscar_consumo_ou_404(db, id_consumo)
    for campo, valor in dados.model_dump().items():
        setattr(obj, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Valor duplicado ou referência inexistente")
    db.refresh(obj)
    return obj
 