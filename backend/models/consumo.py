"""Modelos de CONSUMO (energia de uma máquina em um período)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ConsumoCreate(BaseModel):
    data_inicio: datetime
    data_fim: datetime
    consumo_kwh: float = Field(ge=0, le=1_000_000_000)
    id_maquina: int = Field(gt=0)

    @field_validator("consumo_kwh")
    @classmethod
    def duas_casas(cls, valor: float) -> float:
        return round(valor, 2)

    @model_validator(mode="after")
    def validar_periodo(self):
        if self.data_fim <= self.data_inicio:
            raise ValueError("data_fim deve ser maior que data_inicio")
        return self


class ConsumoResponse(BaseModel):
    id_consumo: int
    data_inicio: datetime
    data_fim: datetime
    consumo_kwh: float
    id_maquina: int
    nome_maquina: Optional[str] = None
    duracao_h: Optional[float] = None
    media_kwh_h: Optional[float] = None
    custo_estimado: Optional[float] = None
    leituras_agregadas: int = 0
    valores_leituras: list[float] = []
    decisoes_acionadas: Optional[list[str]] = None

    model_config = ConfigDict(from_attributes=True)


class CalculoConsumoResponse(BaseModel):
    """Soma das leituras dos sensores da máquina no período."""
    id_maquina: int
    data_inicio: datetime
    data_fim: datetime
    total_kwh: float
    leituras: int
