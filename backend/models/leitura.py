"""Modelos de LEITURA (medições individuais de energia)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LeituraCreate(BaseModel):
    data_leitura: Optional[datetime] = Field(default=None, description="Se não vier, usa o horário atual de Brasília")
    valor_medido_kwh: float = Field(ge=0, le=1_000_000_000, description="Energia medida no intervalo (kWh)")
    observacao_leitura: Optional[str] = Field(default=None, max_length=500)
    id_sensor: int = Field(gt=0)
    id_usuario: Optional[int] = Field(default=None, gt=0, description="Responsável; vazio = coleta automática")

    @field_validator("valor_medido_kwh")
    @classmethod
    def duas_casas(cls, valor: float) -> float:
        return round(valor, 2)

    @field_validator("observacao_leitura")
    @classmethod
    def vazio_vira_nulo(cls, valor: Optional[str]) -> Optional[str]:
        return (valor or "").strip() or None


class LeituraSensorEntrada(BaseModel):
    """Envio direto de um sensor físico (autenticado pelo token do sensor)."""
    valor_medido_kwh: float = Field(ge=0, le=1_000_000_000)
    data_leitura: Optional[datetime] = None
    observacao_leitura: Optional[str] = Field(default=None, max_length=500)


class LeituraResponse(BaseModel):
    id_leitura: int
    data_leitura: datetime
    valor_medido_kwh: float
    observacao_leitura: Optional[str] = None
    id_sensor: int
    id_usuario: Optional[int] = None
    id_consumo: Optional[int] = None
    numero_serie_sensor: Optional[str] = None
    decisoes_acionadas: Optional[list[str]] = None

    model_config = ConfigDict(from_attributes=True)
