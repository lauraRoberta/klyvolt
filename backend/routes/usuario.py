from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db
from seguranca import gerar_hash_senha
from schemas_update import UsuarioUpdate

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


def buscar_usuario_ou_404(db: Session, id_usuario: int) -> models.Usuario:
    obj = db.get(models.Usuario, id_usuario)
    if obj is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado(a)")
    return obj
 
 
@router.get("/{id_usuario}", response_model=schemas.UsuarioResponse)
def obter_usuario(id_usuario: int, db: Session = Depends(get_db)):
    return buscar_usuario_ou_404(db, id_usuario)
 
 
@router.put("/{id_usuario}", response_model=schemas.UsuarioResponse)
def atualizar_usuario(
    id_usuario: int,
    dados: UsuarioUpdate,
    db: Session = Depends(get_db)
):
    obj = buscar_usuario_ou_404(db, id_usuario)
    valores = dados.model_dump()
    senha = valores.pop("senha_usuario", None)
    if senha:  # só troca a senha se ela vier preenchida
        valores["senha_usuario"] = gerar_hash_senha(senha)
    for campo, valor in valores.items():
        setattr(obj, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Valor duplicado ou referência inexistente"
        )
    db.refresh(obj)
    return obj