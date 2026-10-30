"""Modelos de SETOR (áreas da produção da empresa)."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SetorCreate(BaseModel):
    nome_setor: str = Field(min_length=1, max_length=100)
    divisao_setor: Optional[str] = Field(default=None, max_length=100)
    id_usuario_responsavel: int = Field(gt=0)

    @field_validator("nome_setor")
    @classmethod
    def limpar(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("informe o nome do setor")
        return valor


class SetorResponse(BaseModel):
    id_setor: int
    nome_setor: str
    divisao_setor: Optional[str] = None
    id_usuario_responsavel: int
    id_empresa: int
    ativo: Optional[bool] = True
    nome_responsavel: Optional[str] = None
    qtd_maquinas: int = 0

    model_config = ConfigDict(from_attributes=True)
