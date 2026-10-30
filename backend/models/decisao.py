"""Modelos de DECISAO (regras avaliadas automaticamente pelo banco)."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DecisaoCreate(BaseModel):
    nome_decisao: str = Field(min_length=1, max_length=100)
    descricao_decisao: Optional[str] = None
    criterio_acionado: Literal["valor_medido_kwh", "consumo_kwh"] = Field(
        description="valor_medido_kwh = cada leitura; consumo_kwh = consumo agregado do período")
    operador: Literal[">", ">=", "<", "<=", "="]
    limite_referencia: float = Field(ge=0, le=1_000_000_000)
    unidade_limite: Literal["kWh"] = "kWh"
    ativo: bool = True

    @field_validator("nome_decisao")
    @classmethod
    def limpar(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("informe o nome da regra")
        return valor

    @field_validator("descricao_decisao")
    @classmethod
    def vazio_vira_nulo(cls, valor: Optional[str]) -> Optional[str]:
        return (valor or "").strip() or None


class DecisaoResponse(BaseModel):
    id_decisao: int
    nome_decisao: str
    descricao_decisao: Optional[str] = None
    criterio_acionado: str
    operador: str
    limite_referencia: float
    unidade_limite: str
    ativo: Optional[bool] = True
    acionamentos: int = 0
    ultimo_acionamento: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
