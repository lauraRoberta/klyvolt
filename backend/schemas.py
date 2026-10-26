import re
import ipaddress
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


PADRAO_EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


# ---------- Empresa ----------

class EmpresaCreate(BaseModel):
    cnpj: str
    nome_empresa: str = Field(min_length=1, max_length=100)
    email_empresa: str = Field(max_length=100, pattern=PADRAO_EMAIL)
    senha_empresa: str = Field(min_length=6, max_length=72)
    telefone_empresa: str

    @field_validator("cnpj", mode="before")
    @classmethod
    def formatar_cnpj(cls, valor):
        digitos = re.sub(r"\D", "", str(valor))
        if len(digitos) != 14:
            raise ValueError("CNPJ deve ter 14 dígitos")
        return f"{digitos[:2]}.{digitos[2:5]}.{digitos[5:8]}/{digitos[8:12]}-{digitos[12:]}"

    @field_validator("telefone_empresa", mode="before")
    @classmethod
    def formatar_telefone(cls, valor):
        digitos = re.sub(r"\D", "", str(valor))
        # aceita o código do país (+55) e tira ele
        if len(digitos) in (12, 13) and digitos.startswith("55"):
            digitos = digitos[2:]
        if len(digitos) == 11:  # celular
            return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
        if len(digitos) == 10:  # fixo
            return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
        raise ValueError("Telefone deve ter DDD + 8 ou 9 dígitos")

    @field_validator("senha_empresa")
    @classmethod
    def validar_senha(cls, valor):
        if not re.search(r"[A-Za-z]", valor) or not re.search(r"\d", valor):
            raise ValueError("A senha deve ter letras e números")
        return valor

class EmpresaResponse(BaseModel):
    id_empresa: int
    cnpj: str
    nome_empresa: str
    email_empresa: str
    telefone_empresa: str

    model_config = ConfigDict(from_attributes=True)


# ---------- Usuario ----------

class UsuarioCreate(BaseModel):
    nome_usuario: str = Field(min_length=1, max_length=100)
    email_usuario: str = Field(max_length=100, pattern=PADRAO_EMAIL)
    senha_usuario: str
    tipo_usuario: Literal["Administrador", "Operador", "Visualizador"]
    id_empresa: int

@field_validator("senha_usuario")
@classmethod
def validar_senha(cls, valor):
    if not re.search(r"[A-Za-z]", valor) or not re.search(r"\d", valor):
        raise ValueError("A senha deve ter letras e números")
        return valor
    


class UsuarioResponse(BaseModel):
    id_usuario: int
    nome_usuario: str
    email_usuario: str
    tipo_usuario: str
    id_empresa: int

    model_config = ConfigDict(from_attributes=True)


# ---------- Setor ----------

class SetorCreate(BaseModel):
    nome_setor: str = Field(min_length=1, max_length=100)
    divisao_setor: Optional[str] = Field(default=None, max_length=100)
    id_usuario_responsavel: int


class SetorResponse(BaseModel):
    id_setor: int
    nome_setor: str
    divisao_setor: Optional[str] = None
    id_usuario_responsavel: int

    model_config = ConfigDict(from_attributes=True)


# ---------- Maquina ----------

class MaquinaCreate(BaseModel):
    nome_maquina: str = Field(min_length=1, max_length=100)
    descricao_maquina: str = Field(min_length=1)
    potencia_nominal: Optional[float] = Field(default=None, gt=0)
    numero_serie: Optional[str] = Field(default=None, max_length=50)
    id_setor: int


class MaquinaResponse(BaseModel):
    id_maquina: int
    nome_maquina: str
    descricao_maquina: str
    potencia_nominal: Optional[float] = None
    numero_serie: Optional[str] = None
    id_setor: int

    model_config = ConfigDict(from_attributes=True)


# ---------- Sensor ----------

class SensorCreate(BaseModel):
    numero_serie: str = Field(min_length=1, max_length=50)
    fabricante: Optional[str] = Field(default=None, max_length=100)
    modelo: Optional[str] = Field(default=None, max_length=100)
    tipo_sensor: str = Field(min_length=1, max_length=100)
    unidade_medida: str = Field(min_length=1, max_length=10)
    protocolo_comunicacao: str = Field(min_length=1, max_length=50)
    mac_address: str = Field(pattern=r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
    endereco_ip: Optional[str] = Field(default=None, max_length=45)
    token_autenticacao: Optional[str] = Field(default=None, max_length=255)
    status_conexao: Literal["online", "offline", "unknown", "erro"]
    data_instalacao: Optional[date] = None
    data_ultima_calibracao: Optional[date] = None
    status: Literal["ativo", "inativo", "manutencao"]
    id_maquina: int

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
        if (
            self.data_instalacao
            and self.data_ultima_calibracao
            and self.data_ultima_calibracao < self.data_instalacao
        ):
            raise ValueError("data_ultima_calibracao não pode ser anterior à data_instalacao")
        return self


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

    model_config = ConfigDict(from_attributes=True)


# ---------- Consumo ----------

class ConsumoCreate(BaseModel):
    data_inicio: datetime
    data_fim: datetime
    consumo_kwh: float = Field(ge=0)
    id_maquina: int

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

    model_config = ConfigDict(from_attributes=True)


# ---------- Leitura ----------

class LeituraCreate(BaseModel):
    data_leitura: Optional[datetime] = None  # se não vier, o banco usa o horário atual
    valor_medido_kwh: float = Field(ge=0)
    observacao_leitura: Optional[str] = None
    id_sensor: int
    id_usuario: Optional[int] = None
    id_consumo: Optional[int] = None


class LeituraResponse(BaseModel):
    id_leitura: int
    data_leitura: datetime
    valor_medido_kwh: float
    observacao_leitura: Optional[str] = None
    id_sensor: int
    id_usuario: Optional[int] = None
    id_consumo: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# ---------- Decisao ----------

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


# ---------- TomadaDecisao (tem FK para Decisao) ----------

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