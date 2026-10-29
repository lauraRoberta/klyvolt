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


# COLE NO FIM de backend/routes/usuario.py
# Confira no topo do arquivo se existem estes imports (acrescente só os que faltarem):
#   from fastapi import Depends, HTTPException, Response
#   from sqlalchemy.exc import IntegrityError
#   from sqlalchemy.orm import Session
#   from database import get_db
#   import models, schemas
#   from seguranca import gerar_hash   # <- use o nome real da função de hash que o seu POST já usa
#
# No PUT a senha é enviada de novo (o schema de cadastro exige) e vira hash antes de salvar.


@router.get("/{id_usuario}", response_model=schemas.UsuarioResponse)
def buscar_usuario(id_usuario: int, db: Session = Depends(get_db)):
    usuario = db.get(models.Usuario, id_usuario)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return usuario


@router.put("/{id_usuario}", response_model=schemas.UsuarioResponse)
def atualizar_usuario(id_usuario: int, dados: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    usuario = db.get(models.Usuario, id_usuario)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    valores = dados.model_dump()
    valores["senha_usuario"] = gerar_hash(valores["senha_usuario"])
    for campo, valor in valores.items():
        setattr(usuario, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Já existe um usuário com esse e-mail, ou a empresa informada não existe.")
    db.refresh(usuario)
    return usuario


@router.delete("/{id_usuario}", status_code=204)
def excluir_usuario(id_usuario: int, db: Session = Depends(get_db)):
    usuario = db.get(models.Usuario, id_usuario)
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    # Setor.id_usuario_responsavel é RESTRICT: o banco recusaria apagar quem responde por um setor.
    responsavel = (
        db.query(models.Setor)
        .filter(models.Setor.id_usuario_responsavel == id_usuario)
        .first()
    )
    if responsavel is not None:
        raise HTTPException(status_code=409, detail="Este usuário é responsável por um setor e não pode ser excluído.")
    db.delete(usuario)  # as leituras dele ficam sem usuário (SET NULL)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível excluir o usuário.")
    return Response(status_code=204)