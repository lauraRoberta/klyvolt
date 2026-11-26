from fastapi import Depends, FastAPI

from fastapi.middleware.cors import CORSMiddleware

import models
from database import engine
from routes import (
    auth,
    consumo,
    decisao,
    empresa,
    ingestao,
    leitura,
    leitura_sensor,
    maquina,
    painel,
    sensor,
    setor,
    tomada_decisao,
    usuario,
)
from seguranca import permissao_por_metodo

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API Klyvolt",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5501",
        "http://localhost:5501",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/")
def inicio():
    return {"mensagem": "API funcionando"}


# Públicas: login e cadastro de empresa (POST /auth/registrar).
app.include_router(auth.router)

# Envio automático do ESP32 (POST /leituras/sensor): sem login de usuário,
# o ESP32 se identifica pelo token (cabeçalho X-Token-Sensor), salvo em sensor.token_autenticacao.
# Precisa vir ANTES do leitura.router, para não ser confundida com /leituras/{id_leitura}.
app.include_router(leitura_sensor.router)

# Rota antiga do ESP32 (formato vibracoes + estado), substituída pelo leitura_sensor.
# app.include_router(ingestao.router)

# empresa e painel conferem o login dentro do próprio arquivo.
app.include_router(empresa.router)
app.include_router(painel.router)

# Todo o resto exige login. Qualquer pessoa logada consulta (GET);
# quem pode criar, editar e apagar depende da função:
#   - cadastros da estrutura (usuários, setores, máquinas, sensores, decisões): só o administrador
#   - consumo, leituras e tomadas de decisão: administrador e operador
#   - o visualizador só consulta
so_administrador = [Depends(permissao_por_metodo("Administrador"))]
administrador_e_operador = [Depends(permissao_por_metodo("Administrador", "Operador"))]

app.include_router(usuario.router, dependencies=so_administrador)
app.include_router(setor.router, dependencies=so_administrador)
app.include_router(maquina.router, dependencies=so_administrador)
app.include_router(sensor.router, dependencies=so_administrador)
app.include_router(decisao.router, dependencies=so_administrador)
app.include_router(consumo.router, dependencies=administrador_e_operador)
app.include_router(leitura.router, dependencies=administrador_e_operador)
app.include_router(tomada_decisao.router, dependencies=administrador_e_operador)