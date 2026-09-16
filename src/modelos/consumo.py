"""
Modelo da tabela `consumo` - Klyvolt (PostgreSQL)
Gerado a partir do DER final do projeto.
"""

import psycopg2.extras
from conexao import conectar


class Consumo:
    def __init__(self, idconsumo=None, data_inicio=None, data_fim=None, consumo_kwh=None, id_maquina=None):
        self.idconsumo = idconsumo
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        self.consumo_kwh = consumo_kwh
        self.id_maquina = id_maquina

    @staticmethod
    def criar(data_inicio, data_fim, consumo_kwh, id_maquina):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "INSERT INTO consumo (data_inicio, data_fim, consumo_kwh, id_maquina) VALUES (%s, %s, %s, %s) RETURNING idconsumo"
        cursor.execute(sql, (data_inicio, data_fim, consumo_kwh, id_maquina))
        novo_id = cursor.fetchone()[0]
        conexao.commit()
        cursor.close()
        conexao.close()
        return novo_id

    @staticmethod
    def buscar_por_id(id_valor):
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM consumo WHERE idconsumo = %s", (id_valor,))
        resultado = cursor.fetchone()
        cursor.close()
        conexao.close()
        if resultado:
            return Consumo(**resultado)
        return None

    @staticmethod
    def listar_todos():
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM consumo")
        resultados = cursor.fetchall()
        cursor.close()
        conexao.close()
        return [Consumo(**linha) for linha in resultados]

    def atualizar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "UPDATE consumo SET data_inicio = %s, data_fim = %s, consumo_kwh = %s, id_maquina = %s WHERE idconsumo = %s"
        cursor.execute(sql, (self.data_inicio, self.data_fim, self.consumo_kwh, self.id_maquina, self.idconsumo))
        conexao.commit()
        cursor.close()
        conexao.close()

    def deletar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM consumo WHERE idconsumo = %s", (self.idconsumo,))
        conexao.commit()
        cursor.close()
        conexao.close()

    def __repr__(self):
        return f"<Consumo idconsumo={self.idconsumo}>"