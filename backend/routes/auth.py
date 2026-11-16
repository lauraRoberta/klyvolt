from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db
from seguranca import criar_token, empresa_atual, verificar_senha

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=schemas.LoginResponse)
def login(dados: schemas.LoginRequest, db: Session = Depends(get_db)):
    empresa = (
        db.query(models.Empresa)
        .filter(models.Empresa.email_empresa == dados.email_empresa)
        .first()
    )
    if empresa is None or not verificar_senha(dados.senha_empresa, empresa.senha_empresa):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")

    return {
        "access_token": criar_token(empresa.id_empresa),
        "token_type": "bearer",
        "empresa": empresa,
    }


@router.get("/me", response_model=schemas.EmpresaResponse)
def quem_sou_eu(empresa: models.Empresa = Depends(empresa_atual)):
    return empresa