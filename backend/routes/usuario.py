from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db
from escopo import usuario_da_empresa
from schemas_update import UsuarioUpdate
from seguranca import Sessao, gerar_hash_senha, sessao_atual

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
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    # Só dá para criar usuário na própria empresa
    if usuario.id_empresa != sessao.id_empresa:
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
        id_empresa=sessao.id_empresa
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
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    return (
        db.query(models.Usuario)
        .filter(models.Usuario.id_empresa == sessao.id_empresa)
        .all()
    )


@router.get("/{id_usuario}", response_model=schemas.UsuarioResponse)
def obter_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    return usuario_da_empresa(db, id_usuario, sessao.id_empresa)


@router.put("/{id_usuario}", response_model=schemas.UsuarioResponse)
def atualizar_usuario(
    id_usuario: int,
    dados: UsuarioUpdate,
    db: Session = Depends(get_db),
    sessao: Sessao = Depends(sessao_atual)
):
    obj = usuario_da_empresa(db, id_usuario, sessao.id_empresa)
    valores = dados.model_dump()
    valores.pop("id_empresa", None)  # o usuário nunca troca de empresa
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