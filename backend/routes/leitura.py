import secrets
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db

router = APIRouter(
    prefix="/leituras",
    tags=["Leitura"]
)


# ---------- Recebimento das leituras do sensor (ESP32) ----------
# Fica antes das rotas com /{id_leitura} para não haver conflito de caminho.

@router.post(
    "/sensor",
    response_model=schemas.LeituraResponse,
    status_code=201
)
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
        raise HTTPException(
            status_code=401,
            detail="Sensor ou token inválido"
        )

    nova_leitura = models.Leitura(
        id_sensor=dados.id_sensor,
        vibracoes=dados.vibracoes,
        temperatura=dados.temperatura,
        umidade=dados.umidade,
        estado_vibracao=dados.estado,
        media_normal=dados.media_normal
    )

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


# ---------- CRUD de leituras ----------

@router.post(
    "",
    response_model=schemas.LeituraResponse
)
def criar_leitura(
    leitura: schemas.LeituraCreate,
    db: Session = Depends(get_db)
):
    # O sensor é obrigatório e precisa existir
    sensor = (
        db.query(models.Sensor)
        .filter(models.Sensor.id_sensor == leitura.id_sensor)
        .first()
    )

    if sensor is None:
        raise HTTPException(
            status_code=404,
            detail="Sensor não encontrado"
        )

    # Usuário e consumo são opcionais, mas se vierem precisam existir
    if leitura.id_usuario is not None:
        usuario = (
            db.query(models.Usuario)
            .filter(models.Usuario.id_usuario == leitura.id_usuario)
            .first()
        )

        if usuario is None:
            raise HTTPException(
                status_code=404,
                detail="Usuário não encontrado"
            )

    if leitura.id_consumo is not None:
        consumo = (
            db.query(models.Consumo)
            .filter(models.Consumo.id_consumo == leitura.id_consumo)
            .first()
        )

        if consumo is None:
            raise HTTPException(
                status_code=404,
                detail="Consumo não encontrado"
            )

    nova_leitura = models.Leitura(
        valor_medido_kwh=leitura.valor_medido_kwh,
        vibracoes=leitura.vibracoes,
        temperatura=leitura.temperatura,
        umidade=leitura.umidade,
        estado_vibracao=leitura.estado_vibracao,
        media_normal=leitura.media_normal,
        observacao_leitura=leitura.observacao_leitura,
        id_sensor=leitura.id_sensor,
        id_usuario=leitura.id_usuario,
        id_consumo=leitura.id_consumo
    )

    # Se a data não vier, o banco usa o horário atual
    if leitura.data_leitura is not None:
        nova_leitura.data_leitura = leitura.data_leitura

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


@router.get(
    "",
    response_model=list[schemas.LeituraResponse]
)
def listar_leituras(
    limite: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    # O sensor gera uma leitura a cada 10 s, então a lista traz só as mais recentes.
    return (
        db.query(models.Leitura)
        .order_by(models.Leitura.data_leitura.desc())
        .limit(limite)
        .all()
    )


def buscar_leitura_ou_404(db: Session, id_leitura: int) -> models.Leitura:
    obj = db.get(models.Leitura, id_leitura)
    if obj is None:
        raise HTTPException(status_code=404, detail="Leitura não encontrado(a)")
    return obj


@router.get("/{id_leitura}", response_model=schemas.LeituraResponse)
def obter_leitura(id_leitura: int, db: Session = Depends(get_db)):
    return buscar_leitura_ou_404(db, id_leitura)


@router.put("/{id_leitura}", response_model=schemas.LeituraResponse)
def atualizar_leitura(id_leitura: int, dados: schemas.LeituraCreate, db: Session = Depends(get_db)):
    obj = buscar_leitura_ou_404(db, id_leitura)
    for campo, valor in dados.model_dump().items():
        if campo == "data_leitura" and valor is None:
            continue  # coluna obrigatória: mantém a data atual
        setattr(obj, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Valor duplicado ou referência inexistente")
    db.refresh(obj)
    return obj