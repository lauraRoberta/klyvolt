from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db

router = APIRouter(
    prefix="/maquinas",
    tags=["Máquina"]
)


@router.post(
    "",
    response_model=schemas.MaquinaResponse
)
def criar_maquina(
    maquina: schemas.MaquinaCreate,
    db: Session = Depends(get_db)
):
    # Antes de inserir, confere se o setor informado existe
    setor = (
        db.query(models.Setor)
        .filter(models.Setor.id_setor == maquina.id_setor)
        .first()
    )

    if setor is None:
        raise HTTPException(
            status_code=404,
            detail="Setor não encontrado"
        )

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
        raise HTTPException(
            status_code=409,
            detail="Já existe uma máquina com esse número de série"
        )

    db.refresh(nova_maquina)

    return nova_maquina


@router.get(
    "",
    response_model=list[schemas.MaquinaResponse]
)
def listar_maquinas(
    db: Session = Depends(get_db)
):
    return db.query(models.Maquina).all()