"""
Conexão compartilhada com o banco de dados Klyvolt (PostgreSQL).
Usada por todos os arquivos de modelo (empresa.py, usuario.py, etc)
e pelo simulador de sensores.
"""

import psycopg2
from db_config import DB_CONFIG


def conectar():
    return psycopg2.connect(**DB_CONFIG)