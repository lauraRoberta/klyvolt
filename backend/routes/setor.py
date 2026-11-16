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


def buscar_setor_ou_404(db: Session, id_setor: int) -> models.Setor:
    obj = db.get(models.Setor, id_setor)
    if obj is None:
        raise HTTPException(status_code=404, detail="Setor não encontrado(a)")
    return obj
 
 
@router.get("/{id_setor}", response_model=schemas.SetorResponse)
def obter_setor(id_setor: int, db: Session = Depends(get_db)):
    return buscar_setor_ou_404(db, id_setor)
 
 
@router.put("/{id_setor}", response_model=schemas.SetorResponse)
def atualizar_setor(id_setor: int, dados: schemas.SetorCreate, db: Session = Depends(get_db)):
    obj = buscar_setor_ou_404(db, id_setor)
    for campo, valor in dados.model_dump().items():
        setattr(obj, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Valor duplicado ou referência inexistente")
    db.refresh(obj)
    return obj
 
 
@router.delete("/{id_setor}", status_code=204)
def remover_setor(id_setor: int, db: Session = Depends(get_db)):
    obj = buscar_setor_ou_404(db, id_setor)
    try:
        db.delete(obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não pode ser removido: há registros que dependem dele")
 