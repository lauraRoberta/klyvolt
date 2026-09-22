"""
Modelo da tabela `decisao` - Klyvolt (PostgreSQL)
Gerado a partir do DER final do projeto (schema revisado).
"""

import psycopg2.extras
from conexao import conectar


class Decisao:
    def __init__(self, id_decisao=None, nome_decisao=None, descricao_decisao=None, criterio_acionado=None, operador=None, limite_referencia=None, unidade_limite=None):
        self.id_decisao = id_decisao
        self.nome_decisao = nome_decisao
        self.descricao_decisao = descricao_decisao
        self.criterio_acionado = criterio_acionado
        self.operador = operador
        self.limite_referencia = limite_referencia
        self.unidade_limite = unidade_limite

    @staticmethod
    def criar(nome_decisao, descricao_decisao, criterio_acionado, operador, limite_referencia, unidade_limite):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "INSERT INTO decisao (nome_decisao, descricao_decisao, criterio_acionado, operador, limite_referencia, unidade_limite) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_decisao"
        cursor.execute(sql, (nome_decisao, descricao_decisao, criterio_acionado, operador, limite_referencia, unidade_limite))
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
        sql = "UPDATE decisao SET nome_decisao = %s, descricao_decisao = %s, criterio_acionado = %s, operador = %s, limite_referencia = %s, unidade_limite = %s WHERE id_decisao = %s"
        cursor.execute(sql, (self.nome_decisao, self.descricao_decisao, self.criterio_acionado, self.operador, self.limite_referencia, self.unidade_limite, self.id_decisao))
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
