# routes/leitura_sensor.py
# Recebe as leituras enviadas pelo ESP32 (SW-420 e DHT22) e salva na tabela leitura.
#
# O ESP32 manda:
#   POST /leituras/sensor
#   Header: X-Token-Sensor: <token>
#   Body:   {"id_sensor": 1, "valor": 12}
#
# Como funciona a segurança:
#   - O token do ESP32 precisa estar salvo na coluna sensor.token_autenticacao
#     de UM sensor (ex.: o sensor 1, de vibração).
#   - Esse mesmo ESP32 pode enviar leituras de qualquer sensor da MESMA máquina
#     (ex.: sensores 2 e 3, de temperatura e umidade).
#   - Não precisa de login (o ESP32 não tem usuário), o token faz esse papel.

import unicodedata
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
from deps import get_db

router = APIRouter(
    prefix="/leituras",
    tags=["Leituras dos sensores (ESP32)"]
)


# ---------- Formato do que o ESP32 envia ----------
class LeituraSensorEntrada(BaseModel):
    id_sensor: int
    valor: float
    # Opcionais: o ESP32 pode mandar depois, se quiser
    estado_vibracao: Optional[str] = None   # NORMAL, ATENCAO, CRITICO
    media_normal: Optional[float] = None    # referência da calibração


# ---------- Confere o token e descobre qual ESP32 está enviando ----------
def sensor_do_token(
    x_token_sensor: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> models.Sensor:
    if not x_token_sensor:
        raise HTTPException(status_code=401, detail="Token do sensor não enviado")

    sensor_dono = (
        db.query(models.Sensor)
        .filter(models.Sensor.token_autenticacao == x_token_sensor)
        .first()
    )
    if sensor_dono is None:
        raise HTTPException(status_code=401, detail="Token do sensor inválido")

    return sensor_dono


# ---------- Descobre em qual coluna o valor deve ser salvo ----------
def _sem_acento(texto: str) -> str:
    texto = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").lower()


def coluna_do_sensor(sensor: models.Sensor) -> str:
    tipo = _sem_acento(sensor.tipo_sensor)
    unidade = _sem_acento(sensor.unidade_medida)

    if "vibra" in tipo:
        return "vibracoes"
    if "temp" in tipo or "c" == unidade.replace("°", "").strip():
        return "temperatura"
    if "umid" in tipo or unidade.strip() == "%":
        return "umidade"
    if "kwh" in unidade or "energia" in tipo or "consumo" in tipo:
        return "valor_medido_kwh"

    raise HTTPException(
        status_code=422,
        detail=(
            f"Não sei em qual coluna salvar o sensor {sensor.id_sensor} "
            f"(tipo_sensor='{sensor.tipo_sensor}'). Use um tipo com "
            "'vibração', 'temperatura', 'umidade' ou 'energia'."
        ),
    )


# ---------- Rota que recebe a leitura ----------
@router.post("/sensor", status_code=201)
def receber_leitura_sensor(
    dados: LeituraSensorEntrada,
    db: Session = Depends(get_db),
    sensor_dono: models.Sensor = Depends(sensor_do_token),
):
    # 1. O sensor existe?
    sensor = db.get(models.Sensor, dados.id_sensor)
    if sensor is None:
        raise HTTPException(status_code=404, detail=f"Sensor {dados.id_sensor} não encontrado")

    # 2. Esse ESP32 pode enviar leitura desse sensor? (precisa ser da mesma máquina)
    if sensor.id_maquina != sensor_dono.id_maquina:
        raise HTTPException(
            status_code=403,
            detail=f"Este token não pode enviar leituras do sensor {dados.id_sensor}",
        )

    # 3. Monta a leitura colocando o valor na coluna certa
    coluna = coluna_do_sensor(sensor)
    valor = int(round(dados.valor)) if coluna == "vibracoes" else dados.valor

    nova_leitura = models.Leitura(id_sensor=sensor.id_sensor)
    setattr(nova_leitura, coluna, valor)

    if coluna == "vibracoes":
        nova_leitura.estado_vibracao = dados.estado_vibracao
        nova_leitura.media_normal = dados.media_normal

    # data_leitura fica com o horário atual (server_default do banco)
    db.add(nova_leitura)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe uma leitura desse sensor nesse horário",
        )
    db.refresh(nova_leitura)

    print(f"[ESP32] sensor {sensor.id_sensor} ({coluna}) -> {valor}")

    return {
        "mensagem": "Leitura registrada",
        "id_leitura": nova_leitura.id_leitura,
        "id_sensor": sensor.id_sensor,
        "coluna": coluna,
        "valor": valor,
        "data_leitura": nova_leitura.data_leitura,
    }