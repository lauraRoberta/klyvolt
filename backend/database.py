"""Acesso ao Supabase (PostgreSQL) por HTTPS.

Toda configuração de conexão fica aqui, lida do arquivo .env do backend.
O navegador nunca recebe a chave do Supabase: ele conversa só com a FastAPI.

Usamos a chave PÚBLICA do projeto (anon/publishable) junto com o token do
usuário logado. Assim o próprio banco (políticas RLS) também confere se o
usuário pode ver ou alterar cada registro: uma segunda camada de proteção
além das verificações feitas na API.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException
from postgrest.exceptions import APIError
from supabase import Client, ClientOptions, create_client

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()
# Endereço do frontend: usado nos links de confirmação de e-mail e de nova senha
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500").strip().rstrip("/")
# Origens autorizadas no CORS (separadas por vírgula)
CORS_ORIGINS = [
    origem.strip()
    for origem in os.getenv("CORS_ORIGINS", "http://127.0.0.1:5500,http://localhost:5500").split(",")
    if origem.strip()
]

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Configure SUPABASE_URL e SUPABASE_KEY no arquivo backend/.env (veja .env.example)."
    )


def _opcoes(cabecalhos: dict | None = None) -> ClientOptions:
    # A API não guarda sessão: cada requisição traz o token do usuário.
    return ClientOptions(headers=cabecalhos or {}, auto_refresh_token=False, persist_session=False)


def cliente_publico() -> Client:
    """Cliente sem usuário: cadastro, login e recuperação de senha."""
    return create_client(SUPABASE_URL, SUPABASE_KEY, options=_opcoes())


def cliente_usuario(token: str) -> Client:
    """Cliente que age em nome do usuário autenticado (o RLS do banco é aplicado)."""
    return create_client(SUPABASE_URL, SUPABASE_KEY, options=_opcoes({"Authorization": f"Bearer {token}"}))


# ---------------------------------------------------------------------------
# Erros do banco → respostas HTTP compreensíveis
# ---------------------------------------------------------------------------
MENSAGENS_DO_BANCO = {
    "KV_CNPJ_INVALIDO": (422, "CNPJ inválido. Confira os 14 dígitos."),
    "KV_CNPJ_EM_USO": (409, "Este CNPJ já está cadastrado."),
    "KV_EMAIL_EM_USO": (409, "Este e-mail já está cadastrado."),
    "KV_TELEFONE_INVALIDO": (422, "Telefone inválido. Informe DDD + número."),
    "KV_NOME_INVALIDO": (422, "Informe o nome da empresa (até 100 caracteres)."),
    "KV_RESPONSAVEL_OUTRA_EMPRESA": (422, "O responsável precisa ser um usuário da sua empresa."),
    "KV_CONVITE_INVALIDO": (422, "Convite inválido ou expirado."),
    "KV_TOKEN_INVALIDO": (401, "Token de sensor inválido ou sensor inativo."),
    "KV_VALOR_INVALIDO": (422, "Valor de leitura inválido."),
}
RESTRICOES = {
    "chk_mac_formato": "Endereço MAC inválido. Formato: XX:XX:XX:XX:XX:XX.",
    "chk_ip_formato": "Endereço IP inválido.",
    "chk_datas_sensor": "A calibração não pode ser anterior à instalação.",
    "chk_periodo_consumo": "A data final deve ser posterior à data inicial.",
    "chk_consumo_positivo": "O consumo não pode ser negativo.",
    "chk_valor_leitura_positivo": "O valor medido não pode ser negativo.",
    "chk_potencia_positiva": "A potência nominal deve ser maior que zero.",
    "chk_operador": "Operador inválido.",
    "chk_tarifa_kwh": "A tarifa não pode ser negativa.",
}


def traduzir_erro(erro: APIError, duplicado: str | None = None, vinculo: str | None = None) -> HTTPException:
    """Converte um erro do Supabase em HTTPException com status e mensagem adequados."""
    codigo = str(erro.code or "")
    mensagem = str(erro.message or "")
    for chave, (status, texto) in MENSAGENS_DO_BANCO.items():
        if chave in mensagem:
            return HTTPException(status_code=status, detail=texto)
    if codigo in ("PGRST301", "PGRST302", "PGRST303") or "JWT" in mensagem:
        return HTTPException(status_code=401, detail="Sessão inválida ou expirada. Entre novamente.")
    if codigo == "23505":
        return HTTPException(status_code=409, detail=duplicado or "Já existe um registro com esses dados.")
    if codigo == "23503":
        return HTTPException(status_code=409, detail=vinculo or "Este registro está vinculado a outros dados.")
    if codigo == "23514":
        for chave, texto in RESTRICOES.items():
            if chave in mensagem:
                return HTTPException(status_code=422, detail=texto)
        return HTTPException(status_code=422, detail="Dados inválidos. Revise os campos.")
    if codigo in ("22P02", "22007", "22008", "22003", "22023"):
        return HTTPException(status_code=422, detail="Formato de dado inválido. Revise os campos.")
    if codigo == "42501":
        return HTTPException(status_code=403, detail="Seu perfil não tem permissão para esta operação.")
    if codigo == "PGRST116":
        return HTTPException(status_code=404, detail="Registro não encontrado.")
    return HTTPException(status_code=502, detail="O Supabase recusou a operação. Confira a mensagem no terminal.")


def executar(consulta, duplicado: str | None = None, vinculo: str | None = None):
    """Executa uma consulta do Supabase e devolve os dados, traduzindo erros."""
    try:
        return consulta.execute().data
    except APIError as erro:
        raise traduzir_erro(erro, duplicado, vinculo) from erro


def um_registro(linhas: list, nome: str) -> dict:
    """Retorna o único registro da lista ou 404 (inexistente ou de outra empresa)."""
    if not linhas:
        raise HTTPException(status_code=404, detail=f"{nome} não encontrado(a).")
    return linhas[0]
