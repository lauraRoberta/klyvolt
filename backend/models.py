"""
Representa, em Python, as tabelas que já existem no PostgreSQL.
"""

from sqlalchemy import Integer, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Decisao(Base):
    __tablename__ = "decisao"

    id_decisao: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome_decisao: Mapped[str] = mapped_column(String)
    descricao_decisao: Mapped[str] = mapped_column(String)
    criterio_acionado: Mapped[str] = mapped_column(String)
    operador: Mapped[str] = mapped_column(String)
    limite_referencia: Mapped[float] = mapped_column(Numeric)
    unidade_limite: Mapped[str] = mapped_column(String)