"""Cadastra uma empresa de exemplo (com usuários, setores, máquinas, sensores,
consumos, leituras e decisões) para você ver o Painel funcionando.

Uso, dentro da pasta backend e com o venv ativado:
    python dados_exemplo.py            -> cria os dados de exemplo
    python dados_exemplo.py remover    -> apaga tudo o que o script criou
"""
import sys
from datetime import date, datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

import models
from database import SessionLocal
from seguranca import gerar_hash_senha

EMAIL_EMPRESA = "exemplo@klyvolt.com"
NOME_DECISAO = "Alerta de consumo alto (exemplo)"
SETORES = ["Setor de Costura", "Setor de Corte", "Setor de Acabamento"]

# (nome, descrição, potência em kW, posição do setor em SETORES, consumo no mês em kWh)
MAQUINAS = [
    ("Overloque", "Overloque 3 fios", 0.55, 0, 190),
    ("Reta industrial", "Máquina reta industrial", 0.55, 0, 150),
    ("Galoneira", "Galoneira de 2 agulhas", 0.75, 0, 90),
    ("Máquina de corte", "Máquina de corte de tecido", 1.50, 1, 260),
    ("Ferro a vapor", "Ferro a vapor industrial", 2.20, 2, 410),
]


def criar(db):
    if db.query(models.Empresa).filter(models.Empresa.email_empresa == EMAIL_EMPRESA).first():
        print("A empresa de exemplo já existe. Nada foi alterado.")
        return
    if db.query(models.Setor).filter(models.Setor.nome_setor.in_(SETORES)).first():
        print("Já existe um setor com o mesmo nome de um setor do exemplo.")
        print("Mude os nomes em SETORES, no começo deste arquivo, e rode de novo.")
        return

    agora = datetime.now()
    senha = gerar_hash_senha("exemplo123")

    empresa = models.Empresa(
        cnpj="98.765.432/0001-10",
        nome_empresa="Facção Exemplo",
        email_empresa=EMAIL_EMPRESA,
        senha_empresa=senha,
        telefone_empresa="(11) 99999-0000",
    )
    db.add(empresa)
    db.flush()

    admin = models.Usuario(nome_usuario="Marina Souza", email_usuario="marina@exemplo.klyvolt.com",
                           senha_usuario=senha, tipo_usuario="Administrador", id_empresa=empresa.id_empresa)
    operador = models.Usuario(nome_usuario="Carlos Lima", email_usuario="carlos@exemplo.klyvolt.com",
                              senha_usuario=senha, tipo_usuario="Operador", id_empresa=empresa.id_empresa)
    visualizador = models.Usuario(nome_usuario="Ana Ribeiro", email_usuario="ana@exemplo.klyvolt.com",
                                  senha_usuario=senha, tipo_usuario="Visualizador", id_empresa=empresa.id_empresa)
    db.add_all([admin, operador, visualizador])
    db.flush()

    responsaveis = [admin, operador, admin]
    setores = [
        models.Setor(nome_setor=nome, id_usuario_responsavel=responsavel.id_usuario)
        for nome, responsavel in zip(SETORES, responsaveis)
    ]
    db.add_all(setores)
    db.flush()

    maquinas = []
    for i, (nome, descricao, potencia, posicao_setor, _) in enumerate(MAQUINAS, start=1):
        maquinas.append(models.Maquina(
            nome_maquina=nome, descricao_maquina=descricao, potencia_nominal=potencia,
            numero_serie=f"EX-MAQ-{i:03d}", id_setor=setores[posicao_setor].id_setor,
        ))
    db.add_all(maquinas)
    db.flush()

    sensores = []
    for i, maquina in enumerate(maquinas, start=1):
        sensores.append(models.Sensor(
            numero_serie=f"EX-SEN-{i:03d}", fabricante="Exemplo", modelo="Medidor monofásico",
            tipo_sensor="Medidor de energia", unidade_medida="kWh", protocolo_comunicacao="MQTT",
            mac_address=f"AA:BB:CC:00:00:{i:02d}", endereco_ip=f"192.168.0.{10 + i}",
            status_conexao="offline" if maquina.nome_maquina == "Galoneira" else "online",
            data_instalacao=date.today() - timedelta(days=90), status="ativo",
            id_maquina=maquina.id_maquina,
        ))
    db.add_all(sensores)

    inicio_mes = (agora - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
    consumos = [
        models.Consumo(data_inicio=inicio_mes, data_fim=agora, consumo_kwh=dados[4], id_maquina=maquina.id_maquina)
        for dados, maquina in zip(MAQUINAS, maquinas)
    ]
    db.add_all(consumos)
    db.flush()

    # 4 leituras recentes por sensor, ligadas ao consumo da máquina
    leituras_do_ferro = []
    for i, (dados, sensor, consumo) in enumerate(zip(MAQUINAS, sensores, consumos)):
        valor = round(dados[4] / 20, 2)
        for dias in (1, 2, 3, 4):
            leitura = models.Leitura(
                data_leitura=agora - timedelta(days=dias, hours=i),
                valor_medido_kwh=valor, id_sensor=sensor.id_sensor,
                id_usuario=operador.id_usuario, id_consumo=consumo.id_consumo,
            )
            db.add(leitura)
            if dados[0] == "Ferro a vapor":
                leituras_do_ferro.append((leitura, valor))
    db.flush()

    decisao = models.Decisao(
        nome_decisao=NOME_DECISAO,
        descricao_decisao="Registra um alerta quando uma leitura passa do limite.",
        criterio_acionado="Consumo da máquina por leitura",
        operador=">", limite_referencia=15, unidade_limite="kWh",
    )
    db.add(decisao)
    db.flush()

    for (leitura, valor), status in zip(leituras_do_ferro[:2], ["Executada", "Pendente"]):
        db.add(models.TomadaDecisao(
            id_decisao=decisao.id_decisao, valor_referencia=valor, status_execucao=status,
            observacao="Leitura acima do limite (dados de exemplo)",
            id_leitura=leitura.id_leitura, id_consumo=leitura.id_consumo,
        ))

    db.commit()
    print("Pronto! Empresa de exemplo criada: Facção Exemplo")
    print("Entre no sistema com:  marina@exemplo.klyvolt.com  /  senha: exemplo123  (administradora)")
    print("Para apagar tudo depois: python dados_exemplo.py remover")


def remover(db):
    empresa = db.query(models.Empresa).filter(models.Empresa.email_empresa == EMAIL_EMPRESA).first()
    if empresa is None:
        print("Não há empresa de exemplo para remover.")
        return

    ids_usuarios = [u.id_usuario for u in db.query(models.Usuario).filter(models.Usuario.id_empresa == empresa.id_empresa)]
    ids_setores = [s.id_setor for s in db.query(models.Setor).filter(models.Setor.id_usuario_responsavel.in_(ids_usuarios))]
    ids_maquinas = [m.id_maquina for m in db.query(models.Maquina).filter(models.Maquina.id_setor.in_(ids_setores))]
    ids_sensores = [s.id_sensor for s in db.query(models.Sensor).filter(models.Sensor.id_maquina.in_(ids_maquinas))]
    ids_consumos = [c.id_consumo for c in db.query(models.Consumo).filter(models.Consumo.id_maquina.in_(ids_maquinas))]
    ids_leituras = [l.id_leitura for l in db.query(models.Leitura).filter(models.Leitura.id_sensor.in_(ids_sensores))]

    db.query(models.TomadaDecisao).filter(or_(
        models.TomadaDecisao.id_leitura.in_(ids_leituras),
        models.TomadaDecisao.id_consumo.in_(ids_consumos),
    )).delete(synchronize_session=False)
    db.query(models.Leitura).filter(models.Leitura.id_leitura.in_(ids_leituras)).delete(synchronize_session=False)
    db.query(models.Consumo).filter(models.Consumo.id_consumo.in_(ids_consumos)).delete(synchronize_session=False)
    db.query(models.Sensor).filter(models.Sensor.id_sensor.in_(ids_sensores)).delete(synchronize_session=False)
    db.query(models.Maquina).filter(models.Maquina.id_maquina.in_(ids_maquinas)).delete(synchronize_session=False)
    db.query(models.Setor).filter(models.Setor.id_setor.in_(ids_setores)).delete(synchronize_session=False)
    db.query(models.Usuario).filter(models.Usuario.id_usuario.in_(ids_usuarios)).delete(synchronize_session=False)
    db.query(models.Decisao).filter(models.Decisao.nome_decisao == NOME_DECISAO).delete(synchronize_session=False)
    db.query(models.Empresa).filter(models.Empresa.id_empresa == empresa.id_empresa).delete(synchronize_session=False)
    db.commit()
    print("Dados de exemplo removidos.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "remover":
            remover(db)
        else:
            criar(db)
    except IntegrityError as erro:
        db.rollback()
        print("Não foi possível gravar (algum dado duplicado?):", erro.orig)
    finally:
        db.close()
