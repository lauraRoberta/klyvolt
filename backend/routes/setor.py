from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db

router = APIRouter(
    prefix="/setores",
    tags=["Setor"]
)


@router.post(
    "",
    response_model=schemas.SetorResponse
)
def criar_setor(
    setor: schemas.SetorCreate,
    db: Session = Depends(get_db)
):
    # Antes de inserir, confere se o usuário responsável existe
    responsavel = (
        db.query(models.Usuario)
        .filter(models.Usuario.id_usuario == setor.id_usuario_responsavel)
        .first()
    )

    if responsavel is None:
        raise HTTPException(
            status_code=404,
            detail="Usuário responsável não encontrado"
        )

    novo_setor = models.Setor(
        nome_setor=setor.nome_setor,
        divisao_setor=setor.divisao_setor,
        id_usuario_responsavel=setor.id_usuario_responsavel
    )

    db.add(novo_setor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe um setor com esse nome"
        )

    db.refresh(novo_setor)

    return novo_setor


@router.get(
    "",
    response_model=list[schemas.SetorResponse]
)
def listar_setores(
    db: Session = Depends(get_db)
):
    return db.query(models.Setor).all()


@router.get("/{id_setor}", response_model=schemas.SetorResponse)
def buscar_setor(id_setor: int, db: Session = Depends(get_db)):
    setor = db.get(models.Setor, id_setor)
    if setor is None:
        raise HTTPException(status_code=404, detail="Setor não encontrado.")
    return setor
 
 
@router.put("/{id_setor}", response_model=schemas.SetorResponse)
def atualizar_setor(id_setor: int, dados: schemas.SetorCreate, db: Session = Depends(get_db)):
    setor = db.get(models.Setor, id_setor)
    if setor is None:
        raise HTTPException(status_code=404, detail="Setor não encontrado.")
    for campo, valor in dados.model_dump().items():
        setattr(setor, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe um setor com esse nome, ou o usuário responsável não existe.")
    db.refresh(setor)
    return setor
 