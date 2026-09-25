"""
Inicia a aplicação FastAPI e registra as rotas.

Coloque este arquivo em: backend/main.py
Rode com: uvicorn main:app --reload
"""

from fastapi import FastAPI

from routes import decisao

app = FastAPI(title="Klyvolt API")

app.include_router(decisao.router)


@app.get("/")
def raiz():
    return {"mensagem": "API Klyvolt no ar"}