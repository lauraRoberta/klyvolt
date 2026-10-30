"""Modelos de MAQUINA (equipamentos da produção)."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MaquinaCreate(BaseModel):
    nome_maquina: str = Field(min_length=1, max_length=100)
    descricao_maquina: str = Field(min_length=1)
    potencia_nominal: Optional[float] = Field(default=None, gt=0, le=10_000_000, description="Potência em W")
    numero_serie: Optional[str] = Field(default=None, max_length=50)
    id_setor: int = Field(gt=0)

    @field_validator("nome_maquina", "descricao_maquina")
    @classmethod
    def limpar(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("campo obrigatório")
        return valor

    @field_validator("numero_serie")
    @classmethod
    def serie_vazia(cls, valor: Optional[str]) -> Optional[str]:
        return (valor or "").strip() or None


class MaquinaResponse(BaseModel):
    id_maquina: int
    nome_maquina: str
    descricao_maquina: str
    potencia_nominal: Optional[float] = None
    numero_serie: Optional[str] = None
    id_setor: int
    nome_setor: Optional[str] = None
    qtd_sensores: int = 0
    consumo_kwh: Optional[float] = None
    custo_estimado: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)
