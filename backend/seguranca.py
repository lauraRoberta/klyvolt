"""Autenticação e autorização das rotas da API.

Fluxo: o frontend envia o cabeçalho  Authorization: Bearer <token>  recebido
no login. A API confirma o token com o Supabase (que valida a assinatura e a
validade) e carrega o perfil do usuário. Cada rota declara quem pode usá-la:

  usuario_atual   → qualquer usuário autenticado (consulta)
  exigir_operador → Administrador ou Operador (leituras, consumos, acionamentos)
  exigir_admin    → somente Administrador (cadastros da empresa)

As políticas RLS do banco repetem essas regras, como segunda camada.
"""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from postgrest.exceptions import APIError
from supabase import Client

from database import cliente_usuario, traduzir_erro

esquema_bearer = HTTPBearer(
    auto_error=False,
    description="Token de acesso obtido em POST /auth/login (botão Authorize do Swagger).",
)


@dataclass
class Contexto:
    """Quem está fazendo a requisição e o cliente Supabase em nome dele."""
    token: str
    db: Client
    id_usuario: int
    nome_usuario: str
    email_usuario: str
    tipo_usuario: str
    id_empresa: int
    nome_empresa: str
    tarifa_kwh: float | None


def usuario_atual(credenciais: HTTPAuthorizationCredentials | None = Depends(esquema_bearer)) -> Contexto:
    if credenciais is None or not credenciais.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Faça login para continuar.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credenciais.credentials
    db = cliente_usuario(token)
    try:
        perfil = db.rpc("kv_perfil_atual").execute().data
    except APIError as erro:
        excecao = traduzir_erro(erro)
        if excecao.status_code == 401:
            excecao.headers = {"WWW-Authenticate": "Bearer"}
        raise excecao from erro
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sua conta não está vinculada a uma empresa ativa.",
        )
    return Contexto(
        token=token,
        db=db,
        id_usuario=perfil["id_usuario"],
        nome_usuario=perfil["nome_usuario"],
        email_usuario=perfil["email_usuario"],
        tipo_usuario=perfil["tipo_usuario"],
        id_empresa=perfil["id_empresa"],
        nome_empresa=perfil["nome_empresa"],
        tarifa_kwh=float(perfil["tarifa_kwh"]) if perfil.get("tarifa_kwh") is not None else None,
    )


def exigir_operador(contexto: Contexto = Depends(usuario_atual)) -> Contexto:
    if contexto.tipo_usuario not in ("Administrador", "Operador"):
        raise HTTPException(status_code=403, detail="Seu perfil (Visualizador) permite apenas consultas.")
    return contexto


def exigir_admin(contexto: Contexto = Depends(usuario_atual)) -> Contexto:
    if contexto.tipo_usuario != "Administrador":
        raise HTTPException(status_code=403, detail="Somente administradores podem realizar esta operação.")
    return contexto
