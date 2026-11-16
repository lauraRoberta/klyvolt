import re
from typing import Optional

from pydantic import Field, field_validator

from schemas import EmpresaCreate, UsuarioCreate


def _senha_valida(valor: Optional[str]) -> Optional[str]:
    if valor is None or valor == "":
        return None
    if not re.search(r"[A-Za-z]", valor) or not re.search(r"\d", valor):
        raise ValueError("A senha deve ter letras e números")
    return valor


class EmpresaUpdate(EmpresaCreate):
    senha_empresa: Optional[str] = Field(default=None, min_length=6, max_length=72)

    @field_validator("senha_empresa")
    @classmethod
    def validar_senha(cls, valor):
        return _senha_valida(valor)


class UsuarioUpdate(UsuarioCreate):
    senha_usuario: Optional[str] = Field(default=None, min_length=6, max_length=72)

    @field_validator("senha_usuario")
    @classmethod
    def validar_senha(cls, valor):
        return _senha_valida(valor)