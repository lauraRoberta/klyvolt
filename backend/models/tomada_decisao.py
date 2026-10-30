"""Modelos de TOMADA_DECISAO (acionamentos registrados pelo motor de decisão).

O sistema registra o acionamento como "pendente". Não há integração com
equipamentos para desligar máquinas: a equipe executa a ação e atualiza
o status (executada, cancelada ou falha).
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class TomadaDecisaoUpdate(BaseModel):
    status_execucao: Literal["pendente", "executada", "cancelada", "falha"]
    observacao: Optional[str] = Field(default=None, max_length=500)


class TomadaDecisaoResponse(BaseModel):
    id_tomada_decisao: int
    data_tomada_decisao: datetime
    valor_referencia: float
    status_execucao: str
    observacao: Optional[str] = None
    id_decisao: int
    nome_decisao: Optional[str] = None
    id_leitura: Optional[int] = None
    id_consumo: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
