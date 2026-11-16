from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db
from schemas_update import EmpresaUpdate
from seguranca import gerar_hash_senha

router = APIRouter(
    prefix="/empresas",
    tags=["Empresa"]
)


@router.post(
    "",
    response_model=schemas.EmpresaResponse
)
def criar_empresa(
    empresa: schemas.EmpresaCreate,
    db: Session = Depends(get_db)
):
    nova_empresa = models.Empresa(
        cnpj=empresa.cnpj,
        nome_empresa=empresa.nome_empresa,
        email_empresa=empresa.email_empresa,
        # a senha nunca é guardada em texto puro
        senha_empresa=gerar_hash_senha(empresa.senha_empresa),
        telefone_empresa=empresa.telefone_empresa
    )

    db.add(nova_empresa)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="CNPJ ou e-mail já cadastrado"
        )

    db.refresh(nova_empresa)

    return nova_empresa


@router.get(
    "",
    response_model=list[schemas.EmpresaResponse]
)
def listar_empresas(
    db: Session = Depends(get_db)
):
    return db.query(models.Empresa).all()


# ===== Empresa: GET por ID e PUT =====
# Cole no FIM do seu routers/empresa.py, depois das rotas que você já tem.
# Não mexe no POST nem no GET da lista. Imports que ainda não existirem no arquivo:
#   from fastapi import Depends, HTTPException
#   from sqlalchemy.exc import IntegrityError
#   from sqlalchemy.orm import Session
#   import models, schemas
#   from database import get_db  # o mesmo get_db que você já usa
#   from schemas_update import EmpresaUpdate
#   # e a sua função de hash (a mesma do POST), com o nome hash_senha ou ajuste abaixo
# O caminho "/{id_empresa}" é relativo ao prefix do seu router.

def buscar_empresa_ou_404(db: Session, id_empresa: int) -> models.Empresa:
    obj = db.get(models.Empresa, id_empresa)
    if obj is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrado(a)")
    return obj


@router.get("/{id_empresa}", response_model=schemas.EmpresaResponse)
def obter_empresa(id_empresa: int, db: Session = Depends(get_db)):
    return buscar_empresa_ou_404(db, id_empresa)


@router.put("/{id_empresa}", response_model=schemas.EmpresaResponse)
def atualizar_empresa(id_empresa: int, dados: EmpresaUpdate, db: Session = Depends(get_db)):
    obj = buscar_empresa_ou_404(db, id_empresa)
    valores = dados.model_dump()
    senha = valores.pop("senha_empresa", None)
    if senha:  # só troca a senha se ela vier preenchida
        valores["senha_empresa"] = gerar_hash_senha(senha)  # use a MESMA função de hash do seu POST
    for campo, valor in valores.items():
        setattr(obj, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Valor duplicado ou referência inexistente")
    db.refresh(obj)
    return obj