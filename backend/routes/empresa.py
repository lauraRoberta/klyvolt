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


@router.get("/{id_empresa}", response_model=schemas.EmpresaResponse)
def buscar_empresa(id_empresa: int, db: Session = Depends(get_db)):
    return buscar_ou_404(db, models.Empresa, id_empresa, "Empresa")
 
 
@router.put("/{id_empresa}", response_model=schemas.EmpresaResponse)
def atualizar_empresa(id_empresa: int, dados: schemas.EmpresaCreate, db: Session = Depends(get_db)):
    empresa = buscar_ou_404(db, models.Empresa, id_empresa, "Empresa")
    valores = dados.model_dump()
    senha = valores.pop("senha_empresa")
    for campo, valor in valores.items():
        setattr(empresa, campo, valor)
    if senha:  # senha vazia = manter a atual
        empresa.senha_empresa = gerar_hash(senha)
    salvar_ou_409(db, "Já existe uma empresa com esse CNPJ ou e-mail.")
    db.refresh(empresa)
    return empresa
 