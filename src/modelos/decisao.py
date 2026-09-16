"""
Modelo da tabela `decisao` - Klyvolt (PostgreSQL)
Gerado a partir do DER final do projeto.
"""

import psycopg2.extras
from conexao import conectar


class Decisao:
    def __init__(self, id_decisao=None, nome_decisao=None, descricao_decisao=None, criterio_acionado=None, limite_referencia=None):
        self.id_decisao = id_decisao
        self.nome_decisao = nome_decisao
        self.descricao_decisao = descricao_decisao
        self.criterio_acionado = criterio_acionado
        self.limite_referencia = limite_referencia

    @staticmethod
    def criar(nome_decisao, descricao_decisao, criterio_acionado, limite_referencia):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "INSERT INTO decisao (nome_decisao, descricao_decisao, criterio_acionado, limite_referencia) VALUES (%s, %s, %s, %s) RETURNING id_decisao"
        cursor.execute(sql, (nome_decisao, descricao_decisao, criterio_acionado, limite_referencia))
        novo_id = cursor.fetchone()[0]
        conexao.commit()
        cursor.close()
        conexao.close()
        return novo_id

    @staticmethod
    def buscar_por_id(id_valor):
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM decisao WHERE id_decisao = %s", (id_valor,))
        resultado = cursor.fetchone()
        cursor.close()
        conexao.close()
        if resultado:
            return Decisao(**resultado)
        return None

    @staticmethod
    def listar_todos():
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM decisao")
        resultados = cursor.fetchall()
        cursor.close()
        conexao.close()
        return [Decisao(**linha) for linha in resultados]

    def atualizar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "UPDATE decisao SET nome_decisao = %s, descricao_decisao = %s, criterio_acionado = %s, limite_referencia = %s WHERE id_decisao = %s"
        cursor.execute(sql, (self.nome_decisao, self.descricao_decisao, self.criterio_acionado, self.limite_referencia, self.id_decisao))
        conexao.commit()
        cursor.close()
        conexao.close()

    def deletar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM decisao WHERE id_decisao = %s", (self.id_decisao,))
        conexao.commit()
        cursor.close()
        conexao.close()

    def __repr__(self):
        return f"<Decisao id_decisao={self.id_decisao}>"