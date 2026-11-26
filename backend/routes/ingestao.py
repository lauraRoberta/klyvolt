"""Recebimento das leituras do ESP32.

Fica num roteador à parte, SEM exigir login de usuário: quem se identifica é o
sensor, pelo id_sensor + token (cabeçalho X-Token-Sensor). A empresa da leitura
é a do próprio sensor, então ela nunca cai na empresa errada.
"""
#import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db

router = APIRouter(
    prefix="/leituras",
    tags=["Sensor (envio automático)"]
)


#@router.post("/sensor", response_model=schemas.LeituraResponse, status_code=201)
def receber_leitura_do_sensor(
    dados: schemas.LeituraSensorCreate,
    x_token_sensor: Optional[str] = Header(default=None),
    db: Session = Depends(get_db)
):
    sensor = (
        db.query(models.Sensor)
        .filter(models.Sensor.id_sensor == dados.id_sensor)
        .first()
    )

    # Mesma resposta para "sensor não existe" e "token errado",
    # para não revelar quais sensores estão cadastrados.
    token_valido = (
        sensor is not None
        and sensor.token_autenticacao is not None
        and x_token_sensor is not None
        and secrets.compare_digest(sensor.token_autenticacao, x_token_sensor)
    )

    if not token_valido:
        raise HTTPException(status_code=401, detail="Sensor ou token inválido")

    nova_leitura = models.Leitura(
        id_sensor=dados.id_sensor,
        vibracoes=dados.vibracoes,
        temperatura=dados.temperatura,
        umidade=dados.umidade,
        estado_vibracao=dados.estado,
        media_normal=dados.media_normal
    )

    # Chegou leitura: o sensor está conectado
    sensor.status_conexao = "online"

    db.add(nova_leitura)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Já existe uma leitura desse sensor nesse horário"
        )

    db.refresh(nova_leitura)
    return nova_leitura