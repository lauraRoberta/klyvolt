"""Modelos do PAINEL e dos RELATÓRIOS (indicadores calculados com dados reais)."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class ItemConsumo(BaseModel):
    id: int
    nome: str
    grupo: Optional[str] = None      # setor da máquina
    consumo_kwh: float
    custo_estimado: Optional[float] = None
    registros: int


class ConsumoDia(BaseModel):
    data: date
    consumo_kwh: float


class Alerta(BaseModel):
    id_tomada_decisao: int
    data_tomada_decisao: datetime
    nome_decisao: Optional[str] = None
    valor_referencia: float
    status_execucao: str


class RelatorioResponse(BaseModel):
    inicio: date
    fim: date
    dias: int
    tarifa_kwh: Optional[float] = None
    consumo_total_kwh: float
    custo_estimado: Optional[float] = None
    media_diaria_kwh: float
    pico_kwh_h: Optional[float] = None
    periodo_anterior_kwh: float
    variacao_percentual: Optional[float] = None
    registros_consumo: int
    leituras_no_periodo: int
    total_setores: int
    total_maquinas: int
    total_sensores: int
    sensores_online: int
    alertas_pendentes: int
    por_maquina: list[ItemConsumo]
    por_setor: list[ItemConsumo]
    por_dia: list[ConsumoDia]
    alertas_recentes: list[Alerta]
    aviso: Optional[str] = None
