"""Filtros por empresa: cada empresa só enxerga os próprios dados.

Caminho da empresa até cada dado:
    empresa -> usuário -> setor (pelo usuário responsável) -> máquina -> sensor -> leitura
"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

import models


# ---------- Consultas já filtradas pela empresa ----------

def consulta_setores(db: Session, id_empresa: int):
    return (
        db.query(models.Setor)
        .join(models.Usuario, models.Setor.id_usuario_responsavel == models.Usuario.id_usuario)
        .filter(models.Usuario.id_empresa == id_empresa)
    )


def consulta_maquinas(db: Session, id_empresa: int):
    return (
        db.query(models.Maquina)
        .join(models.Setor, models.Maquina.id_setor == models.Setor.id_setor)
        .join(models.Usuario, models.Setor.id_usuario_responsavel == models.Usuario.id_usuario)
        .filter(models.Usuario.id_empresa == id_empresa)
    )


def consulta_sensores(db: Session, id_empresa: int):
    return (
        db.query(models.Sensor)
        .join(models.Maquina, models.Sensor.id_maquina == models.Maquina.id_maquina)
        .join(models.Setor, models.Maquina.id_setor == models.Setor.id_setor)
        .join(models.Usuario, models.Setor.id_usuario_responsavel == models.Usuario.id_usuario)
        .filter(models.Usuario.id_empresa == id_empresa)
    )


def consulta_consumos(db: Session, id_empresa: int):
    return (
        db.query(models.Consumo)
        .join(models.Maquina, models.Consumo.id_maquina == models.Maquina.id_maquina)
        .join(models.Setor, models.Maquina.id_setor == models.Setor.id_setor)
        .join(models.Usuario, models.Setor.id_usuario_responsavel == models.Usuario.id_usuario)
        .filter(models.Usuario.id_empresa == id_empresa)
    )


def consulta_leituras(db: Session, id_empresa: int):
    return (
        db.query(models.Leitura)
        .join(models.Sensor, models.Leitura.id_sensor == models.Sensor.id_sensor)
        .join(models.Maquina, models.Sensor.id_maquina == models.Maquina.id_maquina)
        .join(models.Setor, models.Maquina.id_setor == models.Setor.id_setor)
        .join(models.Usuario, models.Setor.id_usuario_responsavel == models.Usuario.id_usuario)
        .filter(models.Usuario.id_empresa == id_empresa)
    )


# ---------- Busca por id: se for de outra empresa, responde 404 ----------

def _ou_404(consulta, condicao, nome: str):
    obj = consulta.filter(condicao).first()
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{nome} não encontrado(a)")
    return obj


def usuario_da_empresa(db: Session, id_usuario: int, id_empresa: int, nome: str = "Usuário"):
    obj = (
        db.query(models.Usuario)
        .filter(models.Usuario.id_usuario == id_usuario, models.Usuario.id_empresa == id_empresa)
        .first()
    )
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{nome} não encontrado(a)")
    return obj


def setor_da_empresa(db: Session, id_setor: int, id_empresa: int):
    return _ou_404(consulta_setores(db, id_empresa), models.Setor.id_setor == id_setor, "Setor")


def maquina_da_empresa(db: Session, id_maquina: int, id_empresa: int):
    return _ou_404(consulta_maquinas(db, id_empresa), models.Maquina.id_maquina == id_maquina, "Máquina")


def sensor_da_empresa(db: Session, id_sensor: int, id_empresa: int):
    return _ou_404(consulta_sensores(db, id_empresa), models.Sensor.id_sensor == id_sensor, "Sensor")


def consumo_da_empresa(db: Session, id_consumo: int, id_empresa: int):
    return _ou_404(consulta_consumos(db, id_empresa), models.Consumo.id_consumo == id_consumo, "Consumo")


def leitura_da_empresa(db: Session, id_leitura: int, id_empresa: int):
    return _ou_404(consulta_leituras(db, id_empresa), models.Leitura.id_leitura == id_leitura, "Leitura")


# ---------- Decisões e tomadas de decisão ----------
# A decisão pertence direto a uma empresa (coluna id_empresa);
# a tomada de decisão herda a empresa da decisão a que se refere.

def consulta_decisoes(db: Session, id_empresa: int):
    return db.query(models.Decisao).filter(models.Decisao.id_empresa == id_empresa)


def consulta_tomadas(db: Session, id_empresa: int):
    return (
        db.query(models.TomadaDecisao)
        .join(models.Decisao, models.TomadaDecisao.id_decisao == models.Decisao.id_decisao)
        .filter(models.Decisao.id_empresa == id_empresa)
    )


def decisao_da_empresa(db: Session, id_decisao: int, id_empresa: int):
    return _ou_404(consulta_decisoes(db, id_empresa), models.Decisao.id_decisao == id_decisao, "Decisão")


def tomada_da_empresa(db: Session, id_tomada_decisao: int, id_empresa: int):
    return _ou_404(
        consulta_tomadas(db, id_empresa),
        models.TomadaDecisao.id_tomada_decisao == id_tomada_decisao,
        "Tomada de decisão",
    )