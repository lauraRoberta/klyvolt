# ============================================================
# Configuração de conexão com o banco de dados Klyvolt (PostgreSQL local)
# ============================================================
# ATENÇÃO: não suba este arquivo com a senha real para o GitHub.
# Adicione "db_config.py" no .gitignore e crie um
# "db_config.example.py" com valores fictícios no lugar, se for
# versionar o projeto.

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "klyvolt",
    "user": "postgres",
    "password": "SUA_SENHA_AQUI",
}
