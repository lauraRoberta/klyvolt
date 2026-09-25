"""
Descreve o formato dos dados que entram e saem da API.
"""

from pydantic import BaseModel, ConfigDict


class DecisaoCreate(BaseModel):
    nome_decisao: str
    descricao_decisao: str
    criterio_acionado: str
    operador: str
    limite_referencia: float
    unidade_limite: str


class DecisaoResponse(DecisaoCreate):
    id_decisao: int
    model_config = ConfigDict(from_attributes=True)