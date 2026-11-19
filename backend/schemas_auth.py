import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from schemas import PADRAO_EMAIL, EmpresaCreate, EmpresaResponse


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=100)
    senha: str = Field(min_length=1, max_length=72)


class SessaoResponse(BaseModel):
    id_usuario: Optional[int] = None
    nome: str
    funcao: str
    empresa: EmpresaResponse


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    sessao: SessaoResponse


class RegistroEmpresa(EmpresaCreate):
    """Cadastro público: a empresa e o primeiro administrador, de uma vez.
    A senha da empresa não é pedida: usa-se a do administrador."""

    senha_empresa: Optional[str] = Field(default=None, max_length=72)
    nome_admin: str = Field(min_length=1, max_length=100)
    email_admin: str = Field(max_length=100, pattern=PADRAO_EMAIL)
    senha_admin: str = Field(min_length=6, max_length=72)

    @field_validator("senha_empresa")
    @classmethod
    def validar_senha(cls, valor):
        return valor  # campo não usado neste cadastro

    @field_validator("senha_admin")
    @classmethod
    def validar_senha_admin(cls, valor):
        if not re.search(r"[A-Za-z]", valor) or not re.search(r"\d", valor):
            raise ValueError("A senha deve ter letras e números")
        return valor
