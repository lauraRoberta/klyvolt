import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

import models
from deps import get_db  # importar deps carrega o .env antes de ler SECRET_KEY

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY não foi definida no arquivo .env")

ALGORITMO = "HS256"
HORAS_DE_SESSAO = 8

bearer = HTTPBearer(auto_error=False)


def gerar_hash_senha(senha: str) -> str:
    """Gera o hash bcrypt da senha (nunca guardar senha em texto puro)."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, hash_guardado: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), hash_guardado.encode("utf-8"))
    except ValueError:  # ex.: senha com mais de 72 bytes
        return False


@dataclass
class Sessao:
    """Quem está logado: o usuário (ou None, se entrou com a senha da empresa),
    a empresa dele e a função."""
    id_usuario: Optional[int]
    id_empresa: int
    funcao: str
    nome: str
    email: str


def criar_token(sessao: Sessao) -> str:
    expira = datetime.now(timezone.utc) + timedelta(hours=HORAS_DE_SESSAO)
    carga = {
        "sub": str(sessao.id_usuario) if sessao.id_usuario is not None else "empresa",
        "emp": sessao.id_empresa,
        "exp": expira,
    }
    return jwt.encode(carga, SECRET_KEY, algorithm=ALGORITMO)


def sessao_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Sessao:
    """Dependência: exige login. Confere o token e busca o usuário no banco a cada
    requisição, então função e empresa sempre vêm dos dados atuais."""
    erro = HTTPException(
        status_code=401,
        detail="Sessão inválida ou expirada. Entre novamente.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credenciais is None:
        raise erro
    try:
        dados = jwt.decode(credenciais.credentials, SECRET_KEY, algorithms=[ALGORITMO])
        id_empresa = int(dados["emp"])
        sub = dados["sub"]
    except (jwt.PyJWTError, KeyError, ValueError):
        raise erro

    if sub == "empresa":  # entrou com o e-mail e a senha da empresa
        empresa = db.get(models.Empresa, id_empresa)
        if empresa is None:
            raise erro
        return Sessao(None, empresa.id_empresa, "Administrador", empresa.nome_empresa, empresa.email_empresa)

    try:
        id_usuario = int(sub)
    except ValueError:
        raise erro
    usuario = db.get(models.Usuario, id_usuario)
    if usuario is None or usuario.id_empresa != id_empresa:
        raise erro
    return Sessao(usuario.id_usuario, usuario.id_empresa, usuario.tipo_usuario, usuario.nome_usuario, usuario.email_usuario)


def exigir_funcao(*funcoes: str):
    """Dependência: além do login, exige uma das funções (ex.: exigir_funcao("Administrador"))."""
    def verificar(sessao: Sessao = Depends(sessao_atual)) -> Sessao:
        if sessao.funcao not in funcoes:
            raise HTTPException(status_code=403, detail="Você não tem permissão para esta ação.")
        return sessao
    return verificar


def permissao_por_metodo(*funcoes_que_alteram: str):
    """Dependência para um conjunto de rotas: qualquer pessoa logada pode CONSULTAR (GET);
    só as funções informadas podem CRIAR, EDITAR ou APAGAR (POST, PUT, DELETE)."""
    def verificar(request: Request, sessao: Sessao = Depends(sessao_atual)) -> Sessao:
        if request.method not in ("GET", "HEAD", "OPTIONS") and sessao.funcao not in funcoes_que_alteram:
            raise HTTPException(status_code=403, detail="Você não tem permissão para alterar estes dados.")
        return sessao
    return verificar