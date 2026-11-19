from fastapi import Depends, FastAPI

from fastapi.middleware.cors import CORSMiddleware

import models
from database import engine
from routes import (
    auth,
    consumo,
    decisao,
    empresa,
    leitura,
    maquina,
    painel,
    sensor,
    setor,
    tomada_decisao,
    usuario,
)
from seguranca import sessao_atual

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API Klyvolt",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/")
def inicio():
    return {"mensagem": "API funcionando"}


# Públicas: login e cadastro de empresa (POST /auth/registrar).
app.include_router(auth.router)

# empresa e painel conferem o login dentro do próprio arquivo.
app.include_router(empresa.router)
app.include_router(painel.router)

# Todo o resto só funciona com login.
protegido = [Depends(sessao_atual)]
app.include_router(usuario.router, dependencies=protegido)
app.include_router(setor.router, dependencies=protegido)
app.include_router(maquina.router, dependencies=protegido)
app.include_router(sensor.router, dependencies=protegido)
app.include_router(consumo.router, dependencies=protegido)
app.include_router(leitura.router, dependencies=protegido)
app.include_router(decisao.router, dependencies=protegido)
app.include_router(tomada_decisao.router, dependencies=protegido)
