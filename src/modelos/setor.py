"""
Modelo da tabela `setor` - Klyvolt (PostgreSQL)
Gerado a partir do DER final do projeto.
"""

import psycopg2.extras
from conexao import conectar


class Setor:
    def __init__(self, idsetor=None, nome_setor=None, divisao_setor=None, id_usuario=None):
        self.idsetor = idsetor
        self.nome_setor = nome_setor
        self.divisao_setor = divisao_setor
        self.id_usuario = id_usuario

    @staticmethod
    def criar(nome_setor, divisao_setor, id_usuario):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "INSERT INTO setor (nome_setor, divisao_setor, id_usuario) VALUES (%s, %s, %s) RETURNING idsetor"
        cursor.execute(sql, (nome_setor, divisao_setor, id_usuario))
        novo_id = cursor.fetchone()[0]
        conexao.commit()
        cursor.close()
        conexao.close()
        return novo_id

    @staticmethod
    def buscar_por_id(id_valor):
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM setor WHERE idsetor = %s", (id_valor,))
        resultado = cursor.fetchone()
        cursor.close()
        conexao.close()
        if resultado:
            return Setor(**resultado)
        return None

    @staticmethod
    def listar_todos():
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM setor")
        resultados = cursor.fetchall()
        cursor.close()
        conexao.close()
        return [Setor(**linha) for linha in resultados]

    def atualizar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "UPDATE setor SET nome_setor = %s, divisao_setor = %s, id_usuario = %s WHERE idsetor = %s"
        cursor.execute(sql, (self.nome_setor, self.divisao_setor, self.id_usuario, self.idsetor))
        conexao.commit()
        cursor.close()
        conexao.close()

    def deletar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM setor WHERE idsetor = %s", (self.idsetor,))
        conexao.commit()
        cursor.close()
        conexao.close()

    def __repr__(self):
        return f"<Setor idsetor={self.idsetor}>"