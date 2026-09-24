"""
Conexão compartilhada com o banco de dados Klyvolt (PostgreSQL).
Usada por todos os arquivos de modelo (empresa.py, usuario.py, etc)
e pelo simulador de sensores.
"""

import psycopg2
from src.database.db_config import DB_CONFIG


def conectar():
    return psycopg2.connect(**DB_CONFIG)


if __name__ == "__main__":
    conn = conectar()
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT version();")
        print("📦 Versão:", cur.fetchone()[0])
        cur.close()
        conn.close()
        print("🔌 Conexão fechada.")


