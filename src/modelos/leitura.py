"""
Modelo da tabela `leitura` - Klyvolt (PostgreSQL)
Gerado a partir do DER final do projeto (schema revisado).
"""

import psycopg2.extras
from src.database.conexao import conectar


class Leitura:
    def __init__(self, id_leitura=None, data_leitura=None, valor_medido_kwh=None, observacao_leitura=None, id_sensor=None, id_usuario=None, id_consumo=None):
        self.id_leitura = id_leitura
        self.data_leitura = data_leitura
        self.valor_medido_kwh = valor_medido_kwh
        self.observacao_leitura = observacao_leitura
        self.id_sensor = id_sensor
        self.id_usuario = id_usuario
        self.id_consumo = id_consumo

    @staticmethod
    def criar(data_leitura, valor_medido_kwh, observacao_leitura, id_sensor, id_usuario, id_consumo):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "INSERT INTO leitura (data_leitura, valor_medido_kwh, observacao_leitura, id_sensor, id_usuario, id_consumo) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_leitura"
        cursor.execute(sql, (data_leitura, valor_medido_kwh, observacao_leitura, id_sensor, id_usuario, id_consumo))
        novo_id = cursor.fetchone()[0]
        conexao.commit()
        cursor.close()
        conexao.close()
        return novo_id

    @staticmethod
    def buscar_por_id(id_valor):
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM leitura WHERE id_leitura = %s", (id_valor,))
        resultado = cursor.fetchone()
        cursor.close()
        conexao.close()
        if resultado:
            return Leitura(**resultado)
        return None

    @staticmethod
    def listar_todos():
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM leitura")
        resultados = cursor.fetchall()
        cursor.close()
        conexao.close()
        return [Leitura(**linha) for linha in resultados]

    def atualizar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "UPDATE leitura SET data_leitura = %s, valor_medido_kwh = %s, observacao_leitura = %s, id_sensor = %s, id_usuario = %s, id_consumo = %s WHERE id_leitura = %s"
        cursor.execute(sql, (self.data_leitura, self.valor_medido_kwh, self.observacao_leitura, self.id_sensor, self.id_usuario, self.id_consumo, self.id_leitura))
        conexao.commit()
        cursor.close()
        conexao.close()

    def deletar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM leitura WHERE id_leitura = %s", (self.id_leitura,))
        conexao.commit()
        cursor.close()
        conexao.close()

    def __repr__(self):
        return f"<Leitura id_leitura={self.id_leitura}>"
