from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------- Desafio 1: Decisao (tabela simples, só PK) ----------

class DecisaoCreate(BaseModel):
    nome_decisao: str
    descricao_decisao: Optional[str] = None
    criterio_acionado: str
    operador: str  # ex.: ">", ">=", "<", "<=", "="
    limite_referencia: float
    unidade_limite: str  # ex.: "kWh", "W"


class DecisaoResponse(BaseModel):
    id_decisao: int
    nome_decisao: str
    descricao_decisao: Optional[str] = None
    criterio_acionado: str
    operador: str
    limite_referencia: float
    unidade_limite: str

    model_config = ConfigDict(from_attributes=True)


# ---------- Desafio 2: TomadaDecisao (tem FK para Decisao) ----------

class TomadaDecisaoCreate(BaseModel):
    id_decisao: int
    valor_referencia: float
    status_execucao: str
    observacao: Optional[str] = None
    id_leitura: Optional[int] = None
    id_consumo: Optional[int] = None


class TomadaDecisaoResponse(BaseModel):
    id_tomada_decisao: int
    data_tomada_decisao: datetime
    decisao: str  # nome da decisão, não o id
    valor_referencia: float
    status_execucao: str
    observacao: Optional[str] = None
    id_leitura: Optional[int] = None
    id_consumo: Optional[int] = None 