"""Rotas de AUTENTICAÇÃO: login, renovação da sessão, logout, perfil e senha.

O cadastro de uma nova conta é feito em POST /empresas (empresa + administrador)
ou por um administrador em POST /usuarios (membro da equipe).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from postgrest.exceptions import APIError
from supabase_auth.errors import AuthApiError, AuthError, AuthRetryableError

from database import FRONTEND_URL, cliente_publico, cliente_usuario, traduzir_erro
from models.auth import (LoginEntrada, MensagemResponse, NovaSenhaEntrada, PerfilResponse,
                         RecuperarEntrada, RefreshEntrada, SessaoResponse)
from seguranca import Contexto, usuario_atual

router = APIRouter(prefix="/auth", tags=["Autenticação"])

URL_ENTRAR = f"{FRONTEND_URL}/pages/entrar.html"


def erro_auth(erro: AuthError) -> HTTPException:
    """Traduz erros do Supabase Auth para mensagens claras."""
    if isinstance(erro, AuthRetryableError):
        return HTTPException(status_code=503, detail="Não foi possível acessar o Supabase. Tente novamente.")
    texto = str(getattr(erro, "message", "") or erro)
    codigo = str(getattr(erro, "code", "") or "")
    situacao = getattr(erro, "status", None)
    t = texto.lower()
    if "invalid login credentials" in t or codigo == "invalid_credentials":
        return HTTPException(status_code=401, detail="E-mail ou senha incorretos.")
    if "email not confirmed" in t or codigo == "email_not_confirmed":
        return HTTPException(status_code=403, detail="Confirme seu e-mail pelo link enviado antes de entrar.")
    if "already registered" in t or codigo in ("user_already_exists", "email_exists"):
        return HTTPException(status_code=409, detail="Este e-mail já possui conta.")
    if "database error saving new user" in t:
        return HTTPException(status_code=422, detail="Não foi possível criar a conta. Verifique CNPJ, telefone e e-mail.")
    if "password" in t and ("least" in t or "weak" in t):
        return HTTPException(status_code=422, detail="Senha fraca. Use ao menos 8 caracteres com letras e números.")
    if "same" in t and "password" in t:
        return HTTPException(status_code=422, detail="A nova senha deve ser diferente da anterior.")
    if situacao == 429 or "rate limit" in t or "security purposes" in t:
        return HTTPException(status_code=429, detail="Muitas tentativas seguidas. Aguarde alguns instantes.")
    if "refresh token" in t or "jwt" in t or "session" in t or situacao == 401:
        return HTTPException(status_code=401, detail="Sessão inválida ou expirada. Entre novamente.")
    return HTTPException(status_code=400, detail="Não foi possível concluir a autenticação.")


def carregar_perfil(token: str) -> dict | None:
    try:
        return cliente_usuario(token).rpc("kv_perfil_atual").execute().data
    except APIError as erro:
        raise traduzir_erro(erro) from erro


def montar_sessao(sessao, perfil: dict | None) -> SessaoResponse:
    return SessaoResponse(
        access_token=sessao.access_token,
        refresh_token=sessao.refresh_token,
        expires_in=sessao.expires_in or 3600,
        perfil=PerfilResponse(**perfil) if perfil else None,
    )


@router.post("/login", response_model=SessaoResponse, summary="Entrar com e-mail e senha")
def login(dados: LoginEntrada):
    try:
        resposta = cliente_publico().auth.sign_in_with_password({"email": dados.email, "password": dados.senha})
    except AuthError as erro:
        raise erro_auth(erro) from erro
    perfil = carregar_perfil(resposta.session.access_token)
    if not perfil:
        raise HTTPException(status_code=403, detail="Esta conta não está vinculada a uma empresa ativa.")
    return montar_sessao(resposta.session, perfil)


@router.post("/refresh", response_model=SessaoResponse, summary="Renovar a sessão (token expirado)")
def renovar(dados: RefreshEntrada):
    try:
        resposta = cliente_publico().auth.refresh_session(dados.refresh_token)
    except AuthError as erro:
        raise erro_auth(erro) from erro
    if not resposta.session:
        raise HTTPException(status_code=401, detail="Sessão expirada. Entre novamente.")
    return montar_sessao(resposta.session, carregar_perfil(resposta.session.access_token))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Encerrar a sessão")
def logout(contexto: Contexto = Depends(usuario_atual)):
    try:
        cliente_publico().auth.admin.sign_out(contexto.token)
    except AuthError:
        pass  # a sessão local é encerrada no navegador mesmo assim
    return None


@router.get("/me", response_model=PerfilResponse, summary="Perfil do usuário autenticado")
def perfil(contexto: Contexto = Depends(usuario_atual)):
    return PerfilResponse(
        id_usuario=contexto.id_usuario, nome_usuario=contexto.nome_usuario,
        email_usuario=contexto.email_usuario, tipo_usuario=contexto.tipo_usuario,
        id_empresa=contexto.id_empresa, nome_empresa=contexto.nome_empresa, tarifa_kwh=contexto.tarifa_kwh,
    )


@router.post("/recuperar", response_model=MensagemResponse, status_code=status.HTTP_202_ACCEPTED,
             summary="Enviar link de recuperação de senha")
def recuperar(dados: RecuperarEntrada):
    email = dados.email.strip().lower()
    try:
        cliente_publico().auth.reset_password_for_email(email, {"redirect_to": URL_ENTRAR})
    except AuthError as erro:
        excecao = erro_auth(erro)
        if excecao.status_code in (429, 503):
            raise excecao from erro
    # Mesma resposta para e-mails cadastrados ou não (não revela contas)
    return MensagemResponse(mensagem=f"Se {email} estiver cadastrado, você receberá um link para criar uma nova senha.")


@router.post("/nova-senha", response_model=MensagemResponse, summary="Definir nova senha (link do e-mail)")
def nova_senha(dados: NovaSenhaEntrada):
    cliente = cliente_publico()
    try:
        cliente.auth.set_session(dados.access_token, dados.refresh_token)
        cliente.auth.update_user({"password": dados.senha})
    except AuthError as erro:
        raise erro_auth(erro) from erro
    return MensagemResponse(mensagem="Senha alterada com sucesso.")
