"""Modelos de AUTENTICAÇÃO (login, sessão, recuperação de senha)."""
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from models.usuario import PADRAO_EMAIL, validar_senha


class LoginEntrada(BaseModel):
    email: str = Field(max_length=100, pattern=PADRAO_EMAIL)
    senha: str = Field(min_length=1, max_length=72)

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, valor: str) -> str:
        return valor.strip().lower()


class PerfilResponse(BaseModel):
    id_usuario: int
    nome_usuario: str
    email_usuario: str
    tipo_usuario: str
    id_empresa: int
    nome_empresa: str
    tarifa_kwh: Optional[float] = None


class SessaoResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"
    perfil: Optional[PerfilResponse] = None


class RefreshEntrada(BaseModel):
    refresh_token: str = Field(min_length=1)


class RecuperarEntrada(BaseModel):
    email: str = Field(max_length=100, pattern=PADRAO_EMAIL)


class NovaSenhaEntrada(BaseModel):
    """Tokens recebidos no link de recuperação enviado por e-mail."""
    access_token: str = Field(min_length=1)
    refresh_token: str = Field(min_length=1)
    senha: str = Field(max_length=72)

    @field_validator("senha")
    @classmethod
    def checar_senha(cls, valor: str) -> str:
        return validar_senha(valor)


class MensagemResponse(BaseModel):
    mensagem: str
