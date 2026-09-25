"""
Modelo da tabela `maquina` - Klyvolt (PostgreSQL)
Gerado a partir do DER final do projeto (schema revisado).
"""

import psycopg2.extras
from src.database.conexao import conectar


class Maquina:
    def __init__(self, id_maquina=None, nome_maquina=None, descricao_maquina=None, potencia_nominal=None, numero_serie=None, id_setor=None):
        self.id_maquina = id_maquina
        self.nome_maquina = nome_maquina
        self.descricao_maquina = descricao_maquina
        self.potencia_nominal = potencia_nominal
        self.numero_serie = numero_serie
        self.id_setor = id_setor

    @staticmethod
    def criar(nome_maquina, descricao_maquina, potencia_nominal, numero_serie, id_setor):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "INSERT INTO maquina (nome_maquina, descricao_maquina, potencia_nominal, numero_serie, id_setor) VALUES (%s, %s, %s, %s, %s) RETURNING id_maquina"
        cursor.execute(sql, (nome_maquina, descricao_maquina, potencia_nominal, numero_serie, id_setor))
        novo_id = cursor.fetchone()[0]
        conexao.commit()
        cursor.close()
        conexao.close()
        return novo_id

    @staticmethod
    def buscar_por_id(id_valor):
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM maquina WHERE id_maquina = %s", (id_valor,))
        resultado = cursor.fetchone()
        cursor.close()
        conexao.close()
        if resultado:
            return Maquina(**resultado)
        return None

    @staticmethod
    def listar_todos():
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM maquina")
        resultados = cursor.fetchall()
        cursor.close()
        conexao.close()
        return [Maquina(**linha) for linha in resultados]

    def atualizar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "UPDATE maquina SET nome_maquina = %s, descricao_maquina = %s, potencia_nominal = %s, numero_serie = %s, id_setor = %s WHERE id_maquina = %s"
        cursor.execute(sql, (self.nome_maquina, self.descricao_maquina, self.potencia_nominal, self.numero_serie, self.id_setor, self.id_maquina))
        conexao.commit()
        cursor.close()
        conexao.close()

    def deletar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM maquina WHERE id_maquina = %s", (self.id_maquina,))
        conexao.commit()
        cursor.close()
        conexao.close()

    def __repr__(self):
        return f"<Maquina id_maquina={self.id_maquina}>"
