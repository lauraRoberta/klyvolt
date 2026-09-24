"""
Modelo da tabela `tomada_decisao` - Klyvolt (PostgreSQL)
Gerado a partir do DER final do projeto.
"""

import psycopg2.extras
from src.database.conexao import conectar


class TomadaDecisao:
    def __init__(self, id_tomada_decisao=None, data_tomada_decisao=None, valor_referencia=None, status_execucao=None, observacao=None, id_decisao=None, id_leitura=None, id_consumo=None):
        self.id_tomada_decisao = id_tomada_decisao
        self.data_tomada_decisao = data_tomada_decisao
        self.valor_referencia = valor_referencia
        self.status_execucao = status_execucao
        self.observacao = observacao
        self.id_decisao = id_decisao
        self.id_leitura = id_leitura
        self.id_consumo = id_consumo

    @staticmethod
    def criar(data_tomada_decisao, valor_referencia, status_execucao, observacao, id_decisao, id_leitura, id_consumo):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "INSERT INTO tomada_decisao (data_tomada_decisao, valor_referencia, status_execucao, observacao, id_decisao, id_leitura, id_consumo) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id_tomada_decisao"
        cursor.execute(sql, (data_tomada_decisao, valor_referencia, status_execucao, observacao, id_decisao, id_leitura, id_consumo))
        novo_id = cursor.fetchone()[0]
        conexao.commit()
        cursor.close()
        conexao.close()
        return novo_id

    @staticmethod
    def buscar_por_id(id_valor):
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM tomada_decisao WHERE id_tomada_decisao = %s", (id_valor,))
        resultado = cursor.fetchone()
        cursor.close()
        conexao.close()
        if resultado:
            return TomadaDecisao(**resultado)
        return None

    @staticmethod
    def listar_todos():
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM tomada_decisao")
        resultados = cursor.fetchall()
        cursor.close()
        conexao.close()
        return [TomadaDecisao(**linha) for linha in resultados]

    def atualizar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "UPDATE tomada_decisao SET data_tomada_decisao = %s, valor_referencia = %s, status_execucao = %s, observacao = %s, id_decisao = %s, id_leitura = %s, id_consumo = %s WHERE id_tomada_decisao = %s"
        cursor.execute(sql, (self.data_tomada_decisao, self.valor_referencia, self.status_execucao, self.observacao, self.id_decisao, self.id_leitura, self.id_consumo, self.id_tomada_decisao))
        conexao.commit()
        cursor.close()
        conexao.close()

    def deletar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM tomada_decisao WHERE id_tomada_decisao = %s", (self.id_tomada_decisao,))
        conexao.commit()
        cursor.close()
        conexao.close()

    def __repr__(self):
        return f"<TomadaDecisao id_tomada_decisao={self.id_tomada_decisao}>"