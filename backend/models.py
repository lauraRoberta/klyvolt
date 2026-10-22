from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from database import Base


class Decisao(Base):
    """Catálogo de tipos de decisão (ex.: desligar máquina, enviar alerta)."""

    __tablename__ = "decisao"

    id_decisao = Column(
        Integer,
        primary_key=True,
        index=True
    )

    nome_decisao = Column(String(100), nullable=False)
    descricao_decisao = Column(Text, nullable=True)
    criterio_acionado = Column(String(150), nullable=False)
    operador = Column(String(2), nullable=False)
    limite_referencia = Column(Numeric(12, 2), nullable=False)
    unidade_limite = Column(String(10), nullable=False)

    tomadas = relationship(
        "TomadaDecisao",
        back_populates="decisao"
    )


class TomadaDecisao(Base):
    """Registro de uma decisão acionada pelo sistema."""

    __tablename__ = "tomada_decisao"

    id_tomada_decisao = Column(
        Integer,
        primary_key=True,
        index=True
    )

    data_tomada_decisao = Column(
        DateTime,
        default=datetime.now,
        nullable=False
    )

    valor_referencia = Column(Numeric(12, 2), nullable=False)
    status_execucao = Column(String(15), nullable=False)
    observacao = Column(Text, nullable=True)

    id_decisao = Column(
        Integer,
        ForeignKey("decisao.id_decisao"),
        nullable=False
    )

    # Existem no banco, mas as tabelas leitura/consumo ainda não estão
    # mapeadas aqui; por isso ficam como inteiros simples (sem ForeignKey).
    id_leitura = Column(Integer, nullable=True)
    id_consumo = Column(Integer, nullable=True)

    decisao = relationship(
        "Decisao",
        back_populates="tomadas"
    )