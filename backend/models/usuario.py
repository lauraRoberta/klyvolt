"""Modelos de USUARIO (pessoas da empresa que acessam o sistema)."""
import re
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

PADRAO_EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
TipoUsuario = Literal["Administrador", "Operador", "Visualizador"]


def validar_senha(valor: str) -> str:
    """Senha forte: ao menos 8 caracteres, com letras e números."""
    if len(valor) < 8 or not re.search(r"[A-Za-z]", valor) or not re.search(r"\d", valor):
        raise ValueError("a senha deve ter ao menos 8 caracteres, com letras e números")
    return valor


class UsuarioCreate(BaseModel):
    """Administrador cadastra um membro da equipe (com senha inicial)."""
    nome_usuario: str = Field(min_length=1, max_length=100)
    email_usuario: str = Field(max_length=100, pattern=PADRAO_EMAIL)
    tipo_usuario: TipoUsuario
    senha: str = Field(max_length=72, description="Senha inicial (8+ caracteres, letras e números)")

    @field_validator("nome_usuario")
    @classmethod
    def limpar_nome(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("informe o nome")
        return valor

    @field_validator("email_usuario")
    @classmethod
    def normalizar_email(cls, valor: str) -> str:
        return valor.strip().lower()

    @field_validator("senha")
    @classmethod
    def checar_senha(cls, valor: str) -> str:
        return validar_senha(valor)


class UsuarioUpdate(BaseModel):
    nome_usuario: str = Field(min_length=1, max_length=100)
    tipo_usuario: TipoUsuario
    ativo: bool = True


class UsuarioResponse(BaseModel):
    id_usuario: int
    nome_usuario: str
    email_usuario: str
    tipo_usuario: str
    id_empresa: int
    ativo: Optional[bool] = True
    confirmacao_pendente: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)
