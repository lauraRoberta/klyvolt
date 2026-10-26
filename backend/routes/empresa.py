from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db
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