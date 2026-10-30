"""API do KLYVOLT (FastAPI).

Executar dentro da pasta backend, com o ambiente virtual ativo:
    python -m uvicorn main:app --reload
Documentação interativa (Swagger): http://127.0.0.1:8000/docs
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from httpx import RequestError
from postgrest.exceptions import APIError
from supabase_auth.errors import AuthRetryableError

from controller import (auth, consumo, decisao, empresa, leitura, maquina, relatorio, sensor, setor,
                        tomada_decisao, usuario)
from database import CORS_ORIGINS, traduzir_erro

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="KLYVOLT - API de Gestão Energética",
    description=(
        "CRUD das entidades do KLYVOLT com Supabase por HTTPS.\n\n"
        "1. Crie uma empresa em **POST /empresas** ou entre em **POST /auth/login**.\n"
        "2. Copie o `access_token` e clique em **Authorize** para testar as rotas protegidas."
    ),
    version="2.0.0",
)

# O navegador só pode ler as respostas da API se a origem do frontend estiver
# autorizada. As origens ficam no .env (CORS_ORIGINS); padrão: Live Server/http.server na porta 5500.
# Authorization é necessário porque as rotas protegidas recebem o token de login.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["X-Total-Count"],
)

for modulo in (auth, empresa, usuario, setor, maquina, sensor, leitura, consumo, decisao, tomada_decisao, relatorio):
    app.include_router(modulo.router)


@app.get("/", tags=["Status"], summary="Verificar se a API está no ar")
def inicio():
    return {"mensagem": "API KLYVOLT funcionando", "documentacao": "/docs"}


@app.exception_handler(APIError)
async def tratar_erro_supabase(request: Request, erro: APIError):
    excecao = traduzir_erro(erro)
    if excecao.status_code >= 500:
        logger.error("Erro na operação do Supabase: %s", erro)
    return JSONResponse(status_code=excecao.status_code, content={"detail": excecao.detail})


@app.exception_handler(RequestError)
async def tratar_erro_rede(request: Request, erro: RequestError):
    logger.error("Falha de comunicação: %s", type(erro).__name__)
    return JSONResponse(
        status_code=503,
        content={"detail": "Não foi possível acessar o Supabase. Verifique a conexão com a internet."},
    )


@app.exception_handler(AuthRetryableError)
async def tratar_erro_auth_rede(request: Request, erro: AuthRetryableError):
    logger.error("Falha de comunicação com o Supabase Auth: %s", erro)
    return JSONResponse(
        status_code=503,
        content={"detail": "Não foi possível acessar o Supabase. Verifique a conexão com a internet."},
    )
