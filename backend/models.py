from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from database import Base


class Empresa(Base):
    __tablename__ = "empresa"

    id_empresa = Column(Integer, primary_key=True)
    cnpj = Column(String(18), nullable=False, unique=True)
    nome_empresa = Column(String(100), nullable=False)
    email_empresa = Column(String(100), nullable=False, unique=True)
    senha_empresa = Column(String(255), nullable=False)
    telefone_empresa = Column(String(20), nullable=False)


class Usuario(Base):
    __tablename__ = "usuario"

    id_usuario = Column(Integer, primary_key=True)
    nome_usuario = Column(String(100), nullable=False)
    email_usuario = Column(String(100), nullable=False, unique=True)
    senha_usuario = Column(String(255), nullable=False)
    tipo_usuario = Column(String(20), nullable=False)
    id_empresa = Column(Integer, ForeignKey("empresa.id_empresa", ondelete="CASCADE"), nullable=False)


class Setor(Base):
    __tablename__ = "setor"

    id_setor = Column(Integer, primary_key=True)
    nome_setor = Column(String(100), nullable=False, unique=True)
    divisao_setor = Column(String(100))
    id_usuario_responsavel = Column(
        Integer, ForeignKey("usuario.id_usuario", ondelete="RESTRICT"), nullable=False
    )


class Maquina(Base):
    __tablename__ = "maquina"

    id_maquina = Column(Integer, primary_key=True)
    nome_maquina = Column(String(100), nullable=False)
    descricao_maquina = Column(Text, nullable=False)
    potencia_nominal = Column(Numeric(10, 2))
    numero_serie = Column(String(50), unique=True)
    id_setor = Column(Integer, ForeignKey("setor.id_setor", ondelete="CASCADE"), nullable=False)


class Sensor(Base):
    __tablename__ = "sensor"

    id_sensor = Column(Integer, primary_key=True)
    numero_serie = Column(String(50), nullable=False, unique=True)
    fabricante = Column(String(100))
    modelo = Column(String(100))
    tipo_sensor = Column(String(100), nullable=False)
    unidade_medida = Column(String(10), nullable=False)
    protocolo_comunicacao = Column(String(50), nullable=False)
    mac_address = Column(String(17), nullable=False, unique=True)
    endereco_ip = Column(String(45))
    token_autenticacao = Column(String(255), unique=True)
    status_conexao = Column(String(10), nullable=False)
    data_instalacao = Column(Date)
    data_ultima_calibracao = Column(Date)
    status = Column(String(15), nullable=False)
    id_maquina = Column(Integer, ForeignKey("maquina.id_maquina", ondelete="CASCADE"), nullable=False)


class Consumo(Base):
    __tablename__ = "consumo"

    id_consumo = Column(Integer, primary_key=True)
    data_inicio = Column(DateTime, nullable=False)
    data_fim = Column(DateTime, nullable=False)
    consumo_kwh = Column(Numeric(12, 2), nullable=False)
    id_maquina = Column(Integer, ForeignKey("maquina.id_maquina", ondelete="CASCADE"), nullable=False)


class Leitura(Base):
    __tablename__ = "leitura"

    id_leitura = Column(Integer, primary_key=True)
    data_leitura = Column(DateTime, nullable=False, server_default=func.now())
    valor_medido_kwh = Column(Numeric(12, 2), nullable=False)
    observacao_leitura = Column(Text)
    id_sensor = Column(Integer, ForeignKey("sensor.id_sensor", ondelete="CASCADE"), nullable=False)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario", ondelete="SET NULL"))
    id_consumo = Column(Integer, ForeignKey("consumo.id_consumo", ondelete="SET NULL"))


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

    # Agora leitura e consumo estão mapeadas neste arquivo,
    # então as duas colunas viram chaves estrangeiras de verdade.
    id_leitura = Column(
        Integer,
        ForeignKey("leitura.id_leitura", ondelete="SET NULL"),
        nullable=True
    )
    id_consumo = Column(
        Integer,
        ForeignKey("consumo.id_consumo", ondelete="SET NULL"),
        nullable=True
    )

    decisao = relationship(
        "Decisao",
        back_populates="tomadas"
    )