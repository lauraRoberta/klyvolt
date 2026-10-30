from fastapi import FastAPI

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models
from database import engine
from routes import (
    consumo,
    decisao,
    empresa,
    leitura,
    maquina,
    sensor,
    setor,
    tomada_decisao,
    usuario,
)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API Klyvolt",
    version="1.0.0"
)

# Libera o frontend para chamar a API a partir do navegador.
# "*" libera qualquer origem: serve para desenvolvimento.
# Em produção, troque pelo endereço do frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def inicio():
    return {"mensagem": "API funcionando"}


app.include_router(empresa.router)
app.include_router(usuario.router)
app.include_router(setor.router)
app.include_router(maquina.router)
app.include_router(sensor.router)
app.include_router(consumo.router)
app.include_router(leitura.router)
app.include_router(decisao.router)
app.include_router(tomada_decisao.router)