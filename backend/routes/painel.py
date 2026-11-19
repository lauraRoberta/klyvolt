from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

import models
from deps import get_db
from seguranca import Sessao, sessao_atual

router = APIRouter(
    prefix="/painel",
    tags=["Painel"]
)


def _buscar(db: Session, modelo, coluna, ids):
    """Registros de 'modelo' cuja 'coluna' está em 'ids' (lista vazia = nenhum)."""
    if not ids:
        return []
    return db.query(modelo).filter(coluna.in_(ids)).all()


@router.get("/{id_empresa}")
def painel_da_empresa(
    id_empresa: int,
    sessao: Sessao = Depends(sessao_atual),
    db: Session = Depends(get_db)
):
    """Junta tudo o que pertence a uma empresa, seguindo a cadeia do banco:
    empresa -> usuários -> setores -> máquinas -> sensores -> leituras
    (e máquinas -> consumos; decisões ligadas a leituras ou consumos)."""
    # cada empresa só vê o próprio painel
    if id_empresa != sessao.id_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    empresa = db.get(models.Empresa, id_empresa)
    if empresa is None:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    usuarios = db.query(models.Usuario).filter(models.Usuario.id_empresa == id_empresa).all()
    ids_usuarios = [u.id_usuario for u in usuarios]

    # o setor pertence à empresa através do usuário responsável
    setores = _buscar(db, models.Setor, models.Setor.id_usuario_responsavel, ids_usuarios)
    ids_setores = [s.id_setor for s in setores]

    maquinas = _buscar(db, models.Maquina, models.Maquina.id_setor, ids_setores)
    ids_maquinas = [m.id_maquina for m in maquinas]

    sensores = _buscar(db, models.Sensor, models.Sensor.id_maquina, ids_maquinas)
    consumos = _buscar(db, models.Consumo, models.Consumo.id_maquina, ids_maquinas)
    ids_sensores = [s.id_sensor for s in sensores]

    leituras = _buscar(db, models.Leitura, models.Leitura.id_sensor, ids_sensores)
    ids_leituras = [l.id_leitura for l in leituras]
    ids_consumos = [c.id_consumo for c in consumos]

    # decisões tomadas ligadas a uma leitura ou a um consumo desta empresa
    filtros = []
    if ids_leituras:
        filtros.append(models.TomadaDecisao.id_leitura.in_(ids_leituras))
    if ids_consumos:
        filtros.append(models.TomadaDecisao.id_consumo.in_(ids_consumos))
    tomadas = []
    if filtros:
        tomadas = (
            db.query(models.TomadaDecisao)
            .filter(or_(*filtros))
            .order_by(models.TomadaDecisao.data_tomada_decisao.desc())
            .all()
        )

    # dicionários para trocar ids por nomes
    nome_setor = {s.id_setor: s.nome_setor for s in setores}
    nome_maquina = {m.id_maquina: m.nome_maquina for m in maquinas}
    setor_da_maquina = {m.id_maquina: m.id_setor for m in maquinas}
    sensor_por_id = {s.id_sensor: s for s in sensores}

    # consumo somado por máquina e por setor
    kwh_maquina = {}
    for c in consumos:
        kwh_maquina[c.id_maquina] = kwh_maquina.get(c.id_maquina, 0.0) + float(c.consumo_kwh)

    kwh_setor = {id_setor: 0.0 for id_setor in ids_setores}
    for id_maquina, kwh in kwh_maquina.items():
        id_setor = setor_da_maquina[id_maquina]
        kwh_setor[id_setor] += kwh

    consumo_por_maquina = sorted(
        (
            {
                "id_maquina": m.id_maquina,
                "nome": m.nome_maquina,
                "setor": nome_setor[m.id_setor],
                "consumo_kwh": round(kwh_maquina.get(m.id_maquina, 0.0), 2),
            }
            for m in maquinas
        ),
        key=lambda item: item["consumo_kwh"],
        reverse=True,
    )
    consumo_por_setor = sorted(
        (
            {"id_setor": s.id_setor, "nome": s.nome_setor, "consumo_kwh": round(kwh_setor[s.id_setor], 2)}
            for s in setores
        ),
        key=lambda item: item["consumo_kwh"],
        reverse=True,
    )

    # setores pelos quais cada usuário é responsável
    setores_do_usuario = {}
    for s in setores:
        setores_do_usuario.setdefault(s.id_usuario_responsavel, []).append(s.nome_setor)

    ultimas_leituras = sorted(leituras, key=lambda l: l.data_leitura, reverse=True)[:10]

    # última leitura de cada sensor (usada na tela Monitoramento)
    ultima_do_sensor = {}
    for leitura in sorted(leituras, key=lambda l: l.data_leitura, reverse=True):
        ultima_do_sensor.setdefault(leitura.id_sensor, leitura)

    lista_sensores = []
    for s in sensores:
        ultima = ultima_do_sensor.get(s.id_sensor)
        lista_sensores.append({
            "id_sensor": s.id_sensor,
            "numero_serie": s.numero_serie,
            "tipo_sensor": s.tipo_sensor,
            "status": s.status,
            "status_conexao": s.status_conexao,
            "maquina": nome_maquina[s.id_maquina],
            "ultima_leitura": ultima.data_leitura if ultima else None,
            "ultimo_valor_kwh": float(ultima.valor_medido_kwh) if ultima else None,
        })

    # estrutura da empresa: setores com suas máquinas (tela Minha empresa)
    nome_usuario = {u.id_usuario: u.nome_usuario for u in usuarios}
    sensores_por_maquina = {}
    for s in sensores:
        sensores_por_maquina[s.id_maquina] = sensores_por_maquina.get(s.id_maquina, 0) + 1

    estrutura = [
        {
            "id_setor": s.id_setor,
            "nome": s.nome_setor,
            "divisao": s.divisao_setor,
            "responsavel": nome_usuario.get(s.id_usuario_responsavel),
            "consumo_kwh": round(kwh_setor[s.id_setor], 2),
            "maquinas": [
                {
                    "id_maquina": m.id_maquina,
                    "nome": m.nome_maquina,
                    "numero_serie": m.numero_serie,
                    "potencia_nominal": float(m.potencia_nominal) if m.potencia_nominal is not None else None,
                    "sensores": sensores_por_maquina.get(m.id_maquina, 0),
                    "consumo_kwh": round(kwh_maquina.get(m.id_maquina, 0.0), 2),
                }
                for m in maquinas
                if m.id_setor == s.id_setor
            ],
        }
        for s in sorted(setores, key=lambda x: x.nome_setor)
    ]

    return {
        "empresa": {
            "id_empresa": empresa.id_empresa,
            "nome_empresa": empresa.nome_empresa,
            "cnpj": empresa.cnpj,
            "email_empresa": empresa.email_empresa,
            "telefone_empresa": empresa.telefone_empresa,
        },
        "totais": {
            "usuarios": len(usuarios),
            "setores": len(setores),
            "maquinas": len(maquinas),
            "sensores": len(sensores),
            "sensores_online": sum(1 for s in sensores if s.status_conexao == "online"),
            "leituras": len(leituras),
            "consumo_kwh": round(sum(kwh_maquina.values()), 2),
            "decisoes": len(tomadas),
        },
        "consumo_por_maquina": consumo_por_maquina,
        "consumo_por_setor": consumo_por_setor,
        "estrutura": estrutura,
        "usuarios": [
            {
                "id_usuario": u.id_usuario,
                "nome_usuario": u.nome_usuario,
                "email_usuario": u.email_usuario,
                "tipo_usuario": u.tipo_usuario,
                "setores": setores_do_usuario.get(u.id_usuario, []),
            }
            for u in usuarios
        ],
        "sensores": lista_sensores,
        "ultimas_leituras": [
            {
                "id_leitura": l.id_leitura,
                "data_leitura": l.data_leitura,
                "valor_medido_kwh": float(l.valor_medido_kwh),
                "sensor": sensor_por_id[l.id_sensor].numero_serie,
                "maquina": nome_maquina[sensor_por_id[l.id_sensor].id_maquina],
            }
            for l in ultimas_leituras
        ],
        "ultimas_decisoes": [
            {
                "id_tomada_decisao": t.id_tomada_decisao,
                "data_tomada_decisao": t.data_tomada_decisao,
                "decisao": t.decisao.nome_decisao,
                "valor_referencia": float(t.valor_referencia),
                "status_execucao": t.status_execucao,
                "observacao": t.observacao,
            }
            for t in tomadas[:10]
        ],
    }
