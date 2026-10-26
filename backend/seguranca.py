import bcrypt


def gerar_hash_senha(senha: str) -> str:
    """Gera o hash bcrypt da senha (nunca guardar senha em texto puro)."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")