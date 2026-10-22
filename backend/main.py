from fastapi import FastAPI

import models
from database import engine
from routes import decisao, tomada_decisao

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="API Klyvolt",
    version="1.0.0"
)


@app.get("/")
def inicio():
    return {"mensagem": "API funcionando"}


app.include_router(decisao.router)
app.include_router(tomada_decisao.router)