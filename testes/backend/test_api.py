"""Testes da API do KLYVOLT (FastAPI → Supabase).

Pré-requisito: ambiente no ar (testes/subir_ambiente.sh) — API em 127.0.0.1:8000
e Supabase local de testes em 127.0.0.1:54321.
Executar:  python -m pytest testes/backend -v
Todos os dados usados aqui são fictícios.
"""
import random
import uuid
from datetime import date, datetime, timedelta

import httpx
import pytest

API = "http://127.0.0.1:8000"
SUPA = "http://127.0.0.1:54321"


def novo_cnpj() -> str:
    base = [random.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]

    def dv(nums, pesos):
        r = sum(n * p for n, p in zip(nums, pesos)) % 11
        return 0 if r < 2 else 11 - r
    base.append(dv(base, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]))
    base.append(dv(base, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]))
    return "".join(map(str, base))


def nova_empresa(api, sufixo=None):
    sufixo = sufixo or uuid.uuid4().hex[:8]
    dados = {"cnpj": novo_cnpj(), "nome_empresa": f"Confecção Teste {sufixo}", "nome_usuario": "Admin Teste",
             "email": f"admin_{sufixo}@teste.com.br", "telefone": "44999998888", "senha": "Teste2026x"}
    r = api.post("/empresas", json=dados)
    assert r.status_code == 201, r.text
    corpo = r.json()
    return {"token": corpo["sessao"]["access_token"], "perfil": corpo["sessao"]["perfil"], "dados": dados,
            "h": {"Authorization": "Bearer " + corpo["sessao"]["access_token"]}}


@pytest.fixture(scope="session")
def api():
    with httpx.Client(base_url=API, timeout=30) as cliente:
        yield cliente


@pytest.fixture(scope="session")
def supa():
    with httpx.Client(base_url=SUPA, timeout=30) as cliente:
        cliente.post("/__teste/config", json={"confirmarEmail": False, "offline": False})
        yield cliente


@pytest.fixture(scope="session")
def emp_a(api, supa):
    return nova_empresa(api)


@pytest.fixture(scope="session")
def emp_b(api, supa):
    return nova_empresa(api)


@pytest.fixture(scope="session")
def estrutura(api, emp_a):
    """Setor → máquina → sensor da empresa A, usados em vários testes."""
    h = emp_a["h"]
    setor = api.post("/setores", headers=h, json={"nome_setor": "Costura", "divisao_setor": "costura",
                                                  "id_usuario_responsavel": emp_a["perfil"]["id_usuario"]}).json()
    maquina = api.post("/maquinas", headers=h, json={"nome_maquina": "Overloque 01", "descricao_maquina": "Overloque 4 fios",
                                                     "potencia_nominal": 550, "numero_serie": "OVL-" + uuid.uuid4().hex[:6],
                                                     "id_setor": setor["id_setor"]}).json()
    mac = ":".join(f"{random.randint(0, 255):02X}" for _ in range(6))
    token = "tk_teste_" + uuid.uuid4().hex[:10]
    sensor = api.post("/sensores", headers=h, json={
        "numero_serie": "SN-" + uuid.uuid4().hex[:6], "tipo_sensor": "Consumo Elétrico", "unidade_medida": "kWh",
        "protocolo_comunicacao": "MQTT", "mac_address": mac, "token_autenticacao": token,
        "status_conexao": "offline", "status": "ativo", "id_maquina": maquina["id_maquina"]}).json()
    return {"setor": setor, "maquina": maquina, "sensor": sensor, "token_sensor": token}


# ---------------------------------------------------------------- Status / Swagger / CORS
def test_api_no_ar_e_swagger(api):
    assert api.get("/").json()["mensagem"] == "API KLYVOLT funcionando"
    assert api.get("/docs").status_code == 200
    caminhos = api.get("/openapi.json").json()["paths"]
    for rota in ["/empresas", "/usuarios", "/setores", "/maquinas", "/sensores", "/leituras", "/consumos",
                 "/decisoes", "/tomadas-decisao", "/relatorios/resumo", "/auth/login"]:
        assert rota in caminhos


def test_cors_preflight_origem_permitida_e_bloqueada(api):
    ok = api.options("/setores", headers={"Origin": "http://127.0.0.1:5500", "Access-Control-Request-Method": "POST",
                                          "Access-Control-Request-Headers": "content-type,authorization"})
    assert ok.status_code == 200 and ok.headers["access-control-allow-origin"] == "http://127.0.0.1:5500"
    ruim = api.options("/setores", headers={"Origin": "http://127.0.0.1:9999", "Access-Control-Request-Method": "POST"})
    assert ruim.status_code == 400 and "access-control-allow-origin" not in ruim.headers


# ---------------------------------------------------------------- Empresa / autenticação
def test_cadastro_valida_campos(api):
    r = api.post("/empresas", json={"cnpj": "11.222.333/0001-82", "nome_empresa": "X", "nome_usuario": "Y",
                                    "email": "x@x.com", "telefone": "123", "senha": "fraca"})
    assert r.status_code == 422
    erros = " ".join(e["loc"][-1] for e in r.json()["detail"])
    assert "cnpj" in erros and "telefone" in erros and "senha" in erros


def test_cadastro_duplicado_409(api, emp_a):
    d = dict(emp_a["dados"])
    assert api.post("/empresas", json=d).status_code == 409
    d["email"] = "outro_" + d["email"]
    r = api.post("/empresas", json=d)
    assert r.status_code == 409 and "CNPJ" in r.json()["detail"]


def test_login_logout_e_sessao(api, emp_a):
    assert api.post("/auth/login", json={"email": emp_a["dados"]["email"], "senha": "Errada123"}).status_code == 401
    r = api.post("/auth/login", json={"email": emp_a["dados"]["email"], "senha": "Teste2026x"})
    assert r.status_code == 200 and r.json()["perfil"]["tipo_usuario"] == "Administrador"
    sessao = r.json()
    novo = api.post("/auth/refresh", json={"refresh_token": sessao["refresh_token"]})
    assert novo.status_code == 200 and novo.json()["access_token"]
    assert api.post("/auth/refresh", json={"refresh_token": sessao["refresh_token"]}).status_code == 401  # já usado
    h = {"Authorization": "Bearer " + novo.json()["access_token"]}
    assert api.get("/auth/me", headers=h).json()["email_usuario"] == emp_a["dados"]["email"]
    assert api.post("/auth/logout", headers=h).status_code == 204
    assert api.post("/auth/refresh", json={"refresh_token": novo.json()["refresh_token"]}).status_code == 401


def test_sem_token_invalido_e_expirado_401(api, supa, emp_a):
    assert api.get("/maquinas").status_code == 401
    assert api.get("/maquinas", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401
    expirado = supa.get("/__teste/token_expirado", params={"email": emp_a["dados"]["email"]}).json()["token"]
    r = api.get("/maquinas", headers={"Authorization": "Bearer " + expirado})
    assert r.status_code == 401 and "expirada" in r.json()["detail"]


def test_empresa_crud(api, emp_a):
    h = emp_a["h"]
    lista = api.get("/empresas", headers=h).json()
    assert len(lista) == 1
    id_emp = lista[0]["id_empresa"]
    assert api.get(f"/empresas/{id_emp}", headers=h).json()["cnpj"].count(".") == 2
    r = api.put(f"/empresas/{id_emp}", headers=h, json={"nome_empresa": "Confecção Atualizada", "telefone_empresa": "4432221111",
                                                        "tarifa_kwh": 0.9})
    assert r.status_code == 200 and r.json()["tarifa_kwh"] == 0.9 and r.json()["telefone_empresa"] == "(44) 3222-1111"
    assert api.put(f"/empresas/{id_emp}", headers=h, json={"nome_empresa": "X", "telefone_empresa": "44999998888",
                                                           "tarifa_kwh": -1}).status_code == 422


def test_recuperacao_de_senha(api, supa):
    emp = nova_empresa(api)
    r = api.post("/auth/recuperar", json={"email": emp["dados"]["email"]})
    assert r.status_code == 202
    assert api.post("/auth/recuperar", json={"email": "naoexiste@teste.com"}).status_code == 202  # não revela contas
    link = supa.get("/__teste/link", params={"email": emp["dados"]["email"]}).json()
    assert link["redirect_to"].endswith("/pages/entrar.html")
    r = api.post("/auth/nova-senha", json={"access_token": link["access_token"], "refresh_token": link["refresh_token"],
                                            "senha": "NovaSenha2026"})
    assert r.status_code == 200, r.text
    assert api.post("/auth/login", json={"email": emp["dados"]["email"], "senha": "NovaSenha2026"}).status_code == 200


def test_cadastro_com_confirmacao_de_email(api, supa):
    supa.post("/__teste/config", json={"confirmarEmail": True})
    try:
        sufixo = uuid.uuid4().hex[:8]
        dados = {"cnpj": novo_cnpj(), "nome_empresa": "Bordados C", "nome_usuario": "Carla", "email": f"carla_{sufixo}@teste.com",
                 "telefone": "44988887777", "senha": "Borda2026x"}
        r = api.post("/empresas", json=dados)
        assert r.status_code == 201 and r.json()["confirmacao_pendente"] is True and r.json()["sessao"] is None
        r = api.post("/auth/login", json={"email": dados["email"], "senha": dados["senha"]})
        assert r.status_code == 403 and "Confirme" in r.json()["detail"]
        supa.post("/__teste/confirmar", json={"email": dados["email"]})
        assert api.post("/auth/login", json={"email": dados["email"], "senha": dados["senha"]}).status_code == 200
    finally:
        supa.post("/__teste/config", json={"confirmarEmail": False})


# ---------------------------------------------------------------- CRUD das entidades
def test_setor_crud(api, emp_a):
    h, resp = emp_a["h"], emp_a["perfil"]["id_usuario"]
    r = api.post("/setores", headers=h, json={"nome_setor": "Acabamento", "divisao_setor": "acabamento", "id_usuario_responsavel": resp})
    assert r.status_code == 201
    s = r.json()
    assert api.get(f"/setores/{s['id_setor']}", headers=h).json()["nome_responsavel"] == "Admin Teste"
    assert api.post("/setores", headers=h, json={"nome_setor": "Acabamento", "id_usuario_responsavel": resp}).status_code == 409
    r = api.put(f"/setores/{s['id_setor']}", headers=h, json={"nome_setor": "Acabamento Final", "divisao_setor": "acabamento",
                                                              "id_usuario_responsavel": resp})
    assert r.json()["nome_setor"] == "Acabamento Final"
    assert api.delete(f"/setores/{s['id_setor']}", headers=h).status_code == 204
    assert api.get(f"/setores/{s['id_setor']}", headers=h).status_code == 404
    assert api.delete(f"/setores/{s['id_setor']}", headers=h).status_code == 404


def test_maquina_crud(api, emp_a, estrutura):
    h = emp_a["h"]
    dados = {"nome_maquina": "Galoneira 02", "descricao_maquina": "Galoneira", "potencia_nominal": 600,
             "numero_serie": None, "id_setor": estrutura["setor"]["id_setor"]}
    r = api.post("/maquinas", headers=h, json=dados)
    assert r.status_code == 201 and r.json()["nome_setor"] == "Costura"
    m = r.json()
    assert api.post("/maquinas", headers=h, json={**dados, "potencia_nominal": -5}).status_code == 422
    assert api.post("/maquinas", headers=h, json={**dados, "numero_serie": estrutura["maquina"]["numero_serie"]}).status_code == 409
    assert api.put(f"/maquinas/{m['id_maquina']}", headers=h, json={**dados, "nome_maquina": "Galoneira 2B"}).json()["nome_maquina"] == "Galoneira 2B"
    assert len(api.get("/maquinas", headers=h, params={"id_setor": estrutura["setor"]["id_setor"]}).json()) >= 2
    assert api.delete(f"/maquinas/{m['id_maquina']}", headers=h).status_code == 204
    assert api.get(f"/maquinas/{m['id_maquina']}", headers=h).status_code == 404


def test_sensor_crud_e_token_oculto(api, emp_a, estrutura, supa):
    h, s = emp_a["h"], estrutura["sensor"]
    assert "token_autenticacao" not in s
    obtido = api.get(f"/sensores/{s['id_sensor']}", headers=h).json()
    assert "token_autenticacao" not in obtido and obtido["nome_maquina"] == "Overloque 01"
    base = {k: obtido[k] for k in ["numero_serie", "fabricante", "modelo", "tipo_sensor", "unidade_medida", "protocolo_comunicacao",
                                   "mac_address", "endereco_ip", "status_conexao", "data_instalacao", "data_ultima_calibracao",
                                   "status", "id_maquina"]}
    r = api.put(f"/sensores/{s['id_sensor']}", headers=h, json={**base, "fabricante": "Siemens", "token_autenticacao": ""})
    assert r.status_code == 200 and r.json()["fabricante"] == "Siemens"
    token_db = supa.post("/__teste/sql", json={"sql": f"select token_autenticacao from sensor where id_sensor={s['id_sensor']};"}).json()["out"]
    assert token_db == estrutura["token_sensor"]  # edição sem token mantém o atual
    for invalido in [{"mac_address": "ZZ"}, {"endereco_ip": "999.1.1.1"},
                     {"data_instalacao": "2026-10-10", "data_ultima_calibracao": "2026-10-01"}]:
        assert api.put(f"/sensores/{s['id_sensor']}", headers=h, json={**base, **invalido}).status_code == 422


def test_decisoes_leituras_consumos_e_calculos(api, emp_a, estrutura):
    h = emp_a["h"]
    regra = api.post("/decisoes", headers=h, json={"nome_decisao": "Leitura alta", "criterio_acionado": "valor_medido_kwh",
                                                   "operador": ">", "limite_referencia": 10})
    assert regra.status_code == 201
    api.post("/decisoes", headers=h, json={"nome_decisao": "Consumo alto", "criterio_acionado": "consumo_kwh",
                                           "operador": ">=", "limite_referencia": 20})
    hoje = date.today().isoformat()
    sid = estrutura["sensor"]["id_sensor"]
    l1 = api.post("/leituras", headers=h, json={"data_leitura": f"{hoje}T09:00", "valor_medido_kwh": 12.5, "id_sensor": sid})
    assert l1.status_code == 201 and l1.json()["decisoes_acionadas"] == ["Leitura alta"]
    l2 = api.post("/leituras", headers=h, json={"data_leitura": f"{hoje}T10:00", "valor_medido_kwh": 4, "id_sensor": sid})
    assert l2.json()["decisoes_acionadas"] == [] and l2.json()["id_consumo"] is None
    assert api.post("/leituras", headers=h, json={"data_leitura": f"{hoje}T10:00", "valor_medido_kwh": 1, "id_sensor": sid}).status_code == 409
    assert api.post("/leituras", headers=h, json={"valor_medido_kwh": -1, "id_sensor": sid}).status_code == 422

    mid = estrutura["maquina"]["id_maquina"]
    calc = api.get("/consumos/calcular", headers=h, params={"id_maquina": mid, "inicio": f"{hoje}T00:00", "fim": f"{hoje}T23:59:59"})
    assert calc.json()["total_kwh"] == 16.5 and calc.json()["leituras"] == 2
    c = api.post("/consumos", headers=h, json={"data_inicio": f"{hoje}T00:00", "data_fim": f"{hoje}T23:59:59",
                                               "consumo_kwh": 16.5, "id_maquina": mid})
    assert c.status_code == 201 and c.json()["leituras_agregadas"] == 2 and c.json()["decisoes_acionadas"] == []
    assert c.json()["custo_estimado"] == 14.85  # tarifa 0,90 definida em test_empresa_crud
    assert api.get(f"/leituras/{l1.json()['id_leitura']}", headers=h).json()["id_consumo"] == c.json()["id_consumo"]
    up = api.put(f"/consumos/{c.json()['id_consumo']}", headers=h, json={"data_inicio": f"{hoje}T00:00", "data_fim": f"{hoje}T23:59:59",
                                                                       "consumo_kwh": 21, "id_maquina": mid})
    assert up.json()["decisoes_acionadas"] == ["Consumo alto"]
    assert api.post("/consumos", headers=h, json={"data_inicio": f"{hoje}T10:00", "data_fim": f"{hoje}T09:00",
                                                  "consumo_kwh": 1, "id_maquina": mid}).status_code == 422

    tomadas = api.get("/tomadas-decisao", headers=h).json()
    assert len(tomadas) == 2 and all(t["status_execucao"] == "pendente" for t in tomadas)
    t = api.put(f"/tomadas-decisao/{tomadas[0]['id_tomada_decisao']}", headers=h, json={"status_execucao": "executada",
                                                                                       "observacao": "Máquina verificada"})
    assert t.json()["status_execucao"] == "executada"
    # regra com histórico não pode ser excluída; leitura que acionou pode (histórico preservado)
    assert api.delete(f"/decisoes/{regra.json()['id_decisao']}", headers=h).status_code == 409
    assert api.delete(f"/leituras/{l1.json()['id_leitura']}", headers=h).status_code == 204
    assert len(api.get("/tomadas-decisao", headers=h).json()) == 2
    assert api.get("/decisoes", headers=h).json()[1]["acionamentos"] >= 1
    lista = api.get("/leituras", headers=h)
    assert lista.headers["x-total-count"] == "1"


def test_leitura_por_sensor_fisico(api, emp_a, estrutura):
    url = "/leituras/sensor"
    assert api.post(url, headers={"X-Sensor-Token": "token_errado_123"}, json={"valor_medido_kwh": 1}).status_code == 401
    r = api.post(url, headers={"X-Sensor-Token": estrutura["token_sensor"]}, json={"valor_medido_kwh": 0.35,
                                                                                    "observacao_leitura": "LEITURA SIMULADA"})
    assert r.status_code == 201
    s = api.get(f"/sensores/{estrutura['sensor']['id_sensor']}", headers=emp_a["h"]).json()
    assert s["status_conexao"] == "online" and s["qtd_leituras"] >= 2


def test_relatorio_resumo(api, emp_a, estrutura):
    r = api.get("/relatorios/resumo", headers=emp_a["h"])
    assert r.status_code == 200
    d = r.json()
    assert d["consumo_total_kwh"] == 21 and d["custo_estimado"] == 18.9 and d["por_maquina"][0]["nome"] == "Overloque 01"
    assert d["por_setor"][0]["nome"] == "Costura" and sum(x["consumo_kwh"] for x in d["por_dia"]) == 21
    assert d["alertas_pendentes"] == 1 and d["total_maquinas"] >= 1
    assert api.get("/relatorios/resumo", headers=emp_a["h"], params={"inicio": "2026-10-10", "fim": "2026-10-01"}).status_code == 422


# ---------------------------------------------------------------- Equipe e perfis
def test_equipe_convite_e_perfis(api, emp_a, estrutura):
    h = emp_a["h"]
    sufixo = uuid.uuid4().hex[:6]
    r = api.post("/usuarios", headers=h, json={"nome_usuario": "Vera Visual", "email_usuario": f"vera_{sufixo}@teste.com",
                                               "tipo_usuario": "Visualizador", "senha": "Visual2026x"})
    assert r.status_code == 201 and r.json()["id_empresa"] == emp_a["perfil"]["id_empresa"]
    vera = r.json()
    assert api.post("/usuarios", headers=h, json={"nome_usuario": "Dup", "email_usuario": f"vera_{sufixo}@teste.com",
                                                  "tipo_usuario": "Operador", "senha": "Visual2026x"}).status_code == 409
    login = api.post("/auth/login", json={"email": f"vera_{sufixo}@teste.com", "senha": "Visual2026x"}).json()
    hv = {"Authorization": "Bearer " + login["access_token"]}
    assert len(api.get("/maquinas", headers=hv).json()) >= 1          # consulta
    assert api.post("/setores", headers=hv, json={"nome_setor": "X", "id_usuario_responsavel": vera["id_usuario"]}).status_code == 403
    assert api.post("/leituras", headers=hv, json={"valor_medido_kwh": 1, "id_sensor": estrutura["sensor"]["id_sensor"]}).status_code == 403
    assert api.post("/usuarios", headers=hv, json={"nome_usuario": "X", "email_usuario": "x@x.com", "tipo_usuario": "Administrador",
                                                   "senha": "Visual2026x"}).status_code == 403
    # administrador promove a Operador: passa a registrar leituras
    r = api.put(f"/usuarios/{vera['id_usuario']}", headers=h, json={"nome_usuario": "Vera", "tipo_usuario": "Operador", "ativo": True})
    assert r.json()["tipo_usuario"] == "Operador"
    assert api.post("/leituras", headers=hv, json={"valor_medido_kwh": 1, "id_sensor": estrutura["sensor"]["id_sensor"]}).status_code == 201
    assert api.post("/setores", headers=hv, json={"nome_setor": "X", "id_usuario_responsavel": vera["id_usuario"]}).status_code == 403
    # proteções do próprio administrador
    eu = emp_a["perfil"]["id_usuario"]
    assert api.put(f"/usuarios/{eu}", headers=h, json={"nome_usuario": "Admin", "tipo_usuario": "Operador", "ativo": True}).status_code == 422
    assert api.delete(f"/usuarios/{eu}", headers=h).status_code == 422
    # responsável por setor não pode ser removido
    api.put(f"/setores/{estrutura['setor']['id_setor']}", headers=h, json={"nome_setor": "Costura", "divisao_setor": "costura",
                                                                          "id_usuario_responsavel": vera["id_usuario"]})
    r = api.delete(f"/usuarios/{vera['id_usuario']}", headers=h)
    assert r.status_code == 409 and "responsável" in r.json()["detail"]
    api.put(f"/setores/{estrutura['setor']['id_setor']}", headers=h, json={"nome_setor": "Costura", "divisao_setor": "costura",
                                                                          "id_usuario_responsavel": eu})
    assert api.delete(f"/usuarios/{vera['id_usuario']}", headers=h).status_code == 204
    assert api.get("/auth/me", headers=hv).status_code == 403  # conta sem empresa


# ---------------------------------------------------------------- Isolamento entre empresas
def test_isolamento_entre_empresas(api, emp_a, emp_b, estrutura):
    hb = emp_b["h"]
    for rota in ["/setores", "/maquinas", "/sensores", "/leituras", "/consumos", "/decisoes", "/tomadas-decisao"]:
        assert api.get(rota, headers=hb).json() == [], rota
    assert len(api.get("/empresas", headers=hb).json()) == 1 and len(api.get("/usuarios", headers=hb).json()) == 1
    ids = estrutura
    assert api.get(f"/maquinas/{ids['maquina']['id_maquina']}", headers=hb).status_code == 404
    assert api.put(f"/maquinas/{ids['maquina']['id_maquina']}", headers=hb, json={
        "nome_maquina": "hack", "descricao_maquina": "x", "id_setor": ids["setor"]["id_setor"]}).status_code == 404
    assert api.delete(f"/sensores/{ids['sensor']['id_sensor']}", headers=hb).status_code == 404
    r = api.post("/maquinas", headers=hb, json={"nome_maquina": "intrusa", "descricao_maquina": "x", "id_setor": ids["setor"]["id_setor"]})
    assert r.status_code == 403
    r = api.post("/setores", headers=hb, json={"nome_setor": "X", "id_usuario_responsavel": emp_a["perfil"]["id_usuario"]})
    assert r.status_code == 422 and "sua empresa" in r.json()["detail"]
    id_a = emp_a["perfil"]["id_empresa"]
    assert api.put(f"/empresas/{id_a}", headers=hb, json={"nome_empresa": "hack", "telefone_empresa": "44999998888"}).status_code == 404
    assert api.get("/maquinas/" + str(ids["maquina"]["id_maquina"]), headers=emp_a["h"]).json()["nome_maquina"] == "Overloque 01"


# ---------------------------------------------------------------- Falhas e exclusão da empresa
def test_supabase_fora_do_ar_503(api, supa, emp_a):
    supa.post("/__teste/config", json={"offline": True})
    try:
        r = api.get("/maquinas", headers=emp_a["h"])
        assert r.status_code == 503 and "Supabase" in r.json()["detail"]
    finally:
        supa.post("/__teste/config", json={"offline": False})


def test_excluir_empresa_em_cascata(api, supa):
    emp = nova_empresa(api)
    h = emp["h"]
    s = api.post("/setores", headers=h, json={"nome_setor": "S", "id_usuario_responsavel": emp["perfil"]["id_usuario"]}).json()
    api.post("/maquinas", headers=h, json={"nome_maquina": "M", "descricao_maquina": "d", "id_setor": s["id_setor"]})
    id_emp = emp["perfil"]["id_empresa"]
    assert api.delete(f"/empresas/{id_emp}", headers=h).status_code == 204
    restante = supa.post("/__teste/sql", json={"sql": f"select count(*) from setor where id_empresa={id_emp};"}).json()["out"]
    assert restante == "0"
    assert api.get("/auth/me", headers=h).status_code == 403
