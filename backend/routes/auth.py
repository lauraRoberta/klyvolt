import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
import schemas
from deps import get_db
from schemas_auth import LoginRequest, LoginResponse, RegistroEmpresa, SessaoResponse
from seguranca import (
    Sessao,
    criar_token,
    gerar_hash_senha,
    sessao_atual,
    verificar_senha,
)

router = APIRouter(
    prefix="/auth",
    tags=["Autenticação"]
)

# Limite de tentativas de login: 5 erros em 5 minutos bloqueiam aquele e-mail naquele computador.
# (Fica na memória: reiniciar o servidor zera a contagem.)
LIMITE_FALHAS = 5
JANELA_SEGUNDOS = 300
_falhas: dict[str, list[float]] = {}


def _chave(request: Request, email: str) -> str:
    origem = request.client.host if request.client else "?"
    return f"{origem}|{email}"


def _bloqueado(chave: str) -> bool:
    agora = time.time()
    recentes = [t for t in _falhas.get(chave, []) if agora - t < JANELA_SEGUNDOS]
    _falhas[chave] = recentes
    return len(recentes) >= LIMITE_FALHAS


def _dados_da_sessao(sessao: Sessao, empresa: models.Empresa) -> dict:
    return {
        "id_usuario": sessao.id_usuario,
        "nome": sessao.nome,
        "funcao": sessao.funcao,
        "empresa": schemas.EmpresaResponse.model_validate(empresa),
    }


def _resposta_de_login(sessao: Sessao, empresa: models.Empresa) -> dict:
    return {
        "access_token": criar_token(sessao),
        "token_type": "bearer",
        "sessao": _dados_da_sessao(sessao, empresa),
    }


@router.post("/login", response_model=LoginResponse)
def login(dados: LoginRequest, request: Request, db: Session = Depends(get_db)):
    email = dados.email.strip().lower()
    chave = _chave(request, email)

    if _bloqueado(chave):
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas. Aguarde alguns minutos e tente de novo."
        )

    # 1) usuário (e-mail e senha de usuário)
    usuario = (
        db.query(models.Usuario)
        .filter(func.lower(models.Usuario.email_usuario) == email)
        .first()
    )
    if usuario is not None and verificar_senha(dados.senha, usuario.senha_usuario):
        empresa = db.get(models.Empresa, usuario.id_empresa)
        sessao = Sessao(usuario.id_usuario, usuario.id_empresa, usuario.tipo_usuario, usuario.nome_usuario)
        _falhas.pop(chave, None)
        return _resposta_de_login(sessao, empresa)

    # 2) empresa (e-mail e senha da empresa): entra como administrador dela
    empresa = (
        db.query(models.Empresa)
        .filter(func.lower(models.Empresa.email_empresa) == email)
        .first()
    )
    if empresa is not None and verificar_senha(dados.senha, empresa.senha_empresa):
        sessao = Sessao(None, empresa.id_empresa, "Administrador", empresa.nome_empresa)
        _falhas.pop(chave, None)
        return _resposta_de_login(sessao, empresa)

    _falhas.setdefault(chave, []).append(time.time())
    # mesma mensagem para e-mail inexistente e senha errada
    raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")


@router.post("/registrar", response_model=LoginResponse)
def registrar_empresa(dados: RegistroEmpresa, db: Session = Depends(get_db)):
    """Cadastro público: cria a empresa e o primeiro administrador e já devolve o login."""
    email_admin = dados.email_admin.strip()
    ja_existe = (
        db.query(models.Usuario)
        .filter(func.lower(models.Usuario.email_usuario) == email_admin.lower())
        .first()
    )
    if ja_existe is not None:
        raise HTTPException(status_code=409, detail="E-mail do administrador já cadastrado")

    senha_hash = gerar_hash_senha(dados.senha_admin)

    empresa = models.Empresa(
        cnpj=dados.cnpj,
        nome_empresa=dados.nome_empresa,
        email_empresa=dados.email_empresa,
        senha_empresa=senha_hash,
        telefone_empresa=dados.telefone_empresa,
    )
    db.add(empresa)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="CNPJ ou e-mail da empresa já cadastrado")

    admin = models.Usuario(
        nome_usuario=dados.nome_admin,
        email_usuario=email_admin,
        senha_usuario=senha_hash,
        tipo_usuario="Administrador",
        id_empresa=empresa.id_empresa,
    )
    db.add(admin)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="E-mail do administrador já cadastrado")

    db.refresh(empresa)
    db.refresh(admin)
    sessao = Sessao(admin.id_usuario, empresa.id_empresa, admin.tipo_usuario, admin.nome_usuario)
    return _resposta_de_login(sessao, empresa)


@router.get("/me", response_model=SessaoResponse)
def quem_sou_eu(sessao: Sessao = Depends(sessao_atual), db: Session = Depends(get_db)):
    empresa = db.get(models.Empresa, sessao.id_empresa)
    return _dados_da_sessao(sessao, empresa)
