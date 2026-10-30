"""Modelos de EMPRESA (cliente da plataforma)."""
import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.auth import SessaoResponse
from models.usuario import PADRAO_EMAIL, validar_senha


def cnpj_valido(digitos: str) -> bool:
    """Confere os dois dígitos verificadores do CNPJ."""
    if len(digitos) != 14 or len(set(digitos)) == 1:
        return False

    def digito(base: str, pesos: list[int]) -> int:
        resto = sum(int(d) * p for d, p in zip(base, pesos)) % 11
        return 0 if resto < 2 else 11 - resto

    d1 = digito(digitos[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = digito(digitos[:13], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    return digitos[12] == str(d1) and digitos[13] == str(d2)


def formatar_telefone(valor) -> str:
    """Aceita com ou sem +55 e devolve (DD) 99999-9999 ou (DD) 9999-9999."""
    digitos = re.sub(r"\D", "", str(valor))
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        digitos = digitos[2:]
    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    if len(digitos) == 10:
        return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
    raise ValueError("telefone deve ter DDD + 8 ou 9 dígitos")


class EmpresaCreate(BaseModel):
    """Cadastro de uma nova empresa e do seu administrador (conta de acesso)."""
    cnpj: str
    nome_empresa: str = Field(min_length=1, max_length=100)
    nome_usuario: str = Field(min_length=1, max_length=100, description="Nome do administrador")
    email: str = Field(max_length=100, pattern=PADRAO_EMAIL)
    telefone: str
    senha: str = Field(max_length=72)

    @field_validator("cnpj", mode="before")
    @classmethod
    def checar_cnpj(cls, valor):
        digitos = re.sub(r"\D", "", str(valor))
        if not cnpj_valido(digitos):
            raise ValueError("CNPJ inválido (confira os 14 dígitos)")
        return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"

    @field_validator("telefone", mode="before")
    @classmethod
    def checar_telefone(cls, valor):
        return formatar_telefone(valor)

    @field_validator("nome_empresa", "nome_usuario")
    @classmethod
    def limpar(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("campo obrigatório")
        return valor

    @field_validator("email")
    @classmethod
    def normalizar_email(cls, valor: str) -> str:
        return valor.strip().lower()

    @field_validator("senha")
    @classmethod
    def checar_senha(cls, valor: str) -> str:
        return validar_senha(valor)


class EmpresaUpdate(BaseModel):
    nome_empresa: str = Field(min_length=1, max_length=100)
    telefone_empresa: str
    tarifa_kwh: Optional[float] = Field(default=None, ge=0, le=100, description="Tarifa de energia em R$/kWh")

    @field_validator("telefone_empresa", mode="before")
    @classmethod
    def checar_telefone(cls, valor):
        return formatar_telefone(valor)

    @field_validator("nome_empresa")
    @classmethod
    def limpar(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("campo obrigatório")
        return valor


class EmpresaResponse(BaseModel):
    id_empresa: int
    cnpj: str
    nome_empresa: str
    email_empresa: str
    telefone_empresa: str
    tarifa_kwh: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class CadastroEmpresaResponse(BaseModel):
    """Resultado do cadastro: entra direto (sessão) ou aguarda confirmação do e-mail."""
    confirmacao_pendente: bool
    mensagem: str
    sessao: Optional[SessaoResponse] = None
