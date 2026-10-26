from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db
from seguranca import gerar_hash_senha

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuário"]
)


@router.post(
    "",
    response_model=schemas.UsuarioResponse
)
def criar_usuario(
    usuario: schemas.UsuarioCreate,
    db: Session = Depends(get_db)
):
    # Antes de inserir, confere se a empresa informada existe
    empresa = (
        db.query(models.Empresa)
        .filter(models.Empresa.id_empresa == usuario.id_empresa)
        .first()
    )

    if empresa is None:
        raise HTTPException(
            status_code=404,
            detail="Empresa não encontrada"
        )

    novo_usuario = models.Usuario(
        nome_usuario=usuario.nome_usuario,
        email_usuario=usuario.email_usuario,
        # a senha nunca é guardada em texto puro
        senha_usuario=gerar_hash_senha(usuario.senha_usuario),
        tipo_usuario=usuario.tipo_usuario,
        id_empresa=usuario.id_empresa
    )

    db.add(novo_usuario)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="E-mail já cadastrado"
        )

    db.refresh(novo_usuario)

    return novo_usuario


@router.get(
    "",
    response_model=list[schemas.UsuarioResponse]
)
def listar_usuarios(
    db: Session = Depends(get_db)
):
    return db.query(models.Usuario).all()