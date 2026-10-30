"""Modelos de SENSOR (medidores instalados nas máquinas)."""
import ipaddress
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SensorCreate(BaseModel):
    numero_serie: str = Field(min_length=1, max_length=50)
    fabricante: Optional[str] = Field(default=None, max_length=100)
    modelo: Optional[str] = Field(default=None, max_length=100)
    tipo_sensor: str = Field(min_length=1, max_length=100)
    unidade_medida: str = Field(min_length=1, max_length=10)
    protocolo_comunicacao: str = Field(min_length=1, max_length=50)
    mac_address: str = Field(pattern=r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
    endereco_ip: Optional[str] = Field(default=None, max_length=45)
    token_autenticacao: Optional[str] = Field(
        default=None, min_length=8, max_length=255,
        description="Usado pelo equipamento para enviar leituras. Nunca é devolvido pela API. "
                    "Na edição, deixe vazio para manter o atual.")
    status_conexao: Literal["online", "offline", "unknown", "erro"]
    data_instalacao: Optional[date] = None
    data_ultima_calibracao: Optional[date] = None
    status: Literal["ativo", "inativo", "manutencao"]
    id_maquina: int = Field(gt=0)

    @field_validator("mac_address")
    @classmethod
    def maiusculas(cls, valor: str) -> str:
        return valor.upper()

    @field_validator("endereco_ip", "token_autenticacao", "fabricante", "modelo", mode="before")
    @classmethod
    def vazio_vira_nulo(cls, valor):
        if isinstance(valor, str) and not valor.strip():
            return None
        return valor.strip() if isinstance(valor, str) else valor

    @field_validator("endereco_ip")
    @classmethod
    def validar_ip(cls, valor):
        if valor is not None:
            try:
                ipaddress.ip_address(valor)
            except ValueError:
                raise ValueError("endereco_ip deve ser um IPv4 ou IPv6 válido")
        return valor

    @model_validator(mode="after")
    def validar_datas(self):
        if self.data_instalacao and self.data_ultima_calibracao and self.data_ultima_calibracao < self.data_instalacao:
            raise ValueError("data_ultima_calibracao não pode ser anterior à data_instalacao")
        return self


class LeituraRecente(BaseModel):
    data_leitura: datetime
    valor_medido_kwh: float


class SensorResponse(BaseModel):
    # o token de autenticação NÃO é devolvido de propósito
    id_sensor: int
    numero_serie: str
    fabricante: Optional[str] = None
    modelo: Optional[str] = None
    tipo_sensor: str
    unidade_medida: str
    protocolo_comunicacao: str
    mac_address: str
    endereco_ip: Optional[str] = None
    status_conexao: str
    data_instalacao: Optional[date] = None
    data_ultima_calibracao: Optional[date] = None
    status: str
    id_maquina: int
    nome_maquina: Optional[str] = None
    total_kwh: float = 0
    hoje_kwh: float = 0
    pico_kwh: float = 0
    qtd_leituras: int = 0
    ultimas_leituras: list[LeituraRecente] = []

    model_config = ConfigDict(from_attributes=True)
