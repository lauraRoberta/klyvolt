"""
Modelo da tabela `sensor` - Klyvolt (PostgreSQL)
Gerado a partir do DER final do projeto.
"""

import psycopg2.extras
from conexao import conectar


class Sensor:
    def __init__(self, id_sensor=None, numero_serie=None, fabricante=None, modelo=None, tipo_sensor=None, unidade_medida=None, protocolo_comunicacao=None, mac_address=None, endereco_ip=None, token_autenticacao=None, status_conexao=None, data_instalacao=None, data_ultima_calibracao=None, status=None, id_maquina=None):
        self.id_sensor = id_sensor
        self.numero_serie = numero_serie
        self.fabricante = fabricante
        self.modelo = modelo
        self.tipo_sensor = tipo_sensor
        self.unidade_medida = unidade_medida
        self.protocolo_comunicacao = protocolo_comunicacao
        self.mac_address = mac_address
        self.endereco_ip = endereco_ip
        self.token_autenticacao = token_autenticacao
        self.status_conexao = status_conexao
        self.data_instalacao = data_instalacao
        self.data_ultima_calibracao = data_ultima_calibracao
        self.status = status
        self.id_maquina = id_maquina

    @staticmethod
    def criar(numero_serie, fabricante, modelo, tipo_sensor, unidade_medida, protocolo_comunicacao, mac_address, endereco_ip, token_autenticacao, status_conexao, data_instalacao, data_ultima_calibracao, status, id_maquina):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "INSERT INTO sensor (numero_serie, fabricante, modelo, tipo_sensor, unidade_medida, protocolo_comunicacao, mac_address, endereco_ip, token_autenticacao, status_conexao, data_instalacao, data_ultima_calibracao, status, id_maquina) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id_sensor"
        cursor.execute(sql, (numero_serie, fabricante, modelo, tipo_sensor, unidade_medida, protocolo_comunicacao, mac_address, endereco_ip, token_autenticacao, status_conexao, data_instalacao, data_ultima_calibracao, status, id_maquina))
        novo_id = cursor.fetchone()[0]
        conexao.commit()
        cursor.close()
        conexao.close()
        return novo_id

    @staticmethod
    def buscar_por_id(id_valor):
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM sensor WHERE id_sensor = %s", (id_valor,))
        resultado = cursor.fetchone()
        cursor.close()
        conexao.close()
        if resultado:
            return Sensor(**resultado)
        return None

    @staticmethod
    def listar_todos():
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM sensor")
        resultados = cursor.fetchall()
        cursor.close()
        conexao.close()
        return [Sensor(**linha) for linha in resultados]

    def atualizar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "UPDATE sensor SET numero_serie = %s, fabricante = %s, modelo = %s, tipo_sensor = %s, unidade_medida = %s, protocolo_comunicacao = %s, mac_address = %s, endereco_ip = %s, token_autenticacao = %s, status_conexao = %s, data_instalacao = %s, data_ultima_calibracao = %s, status = %s, id_maquina = %s WHERE id_sensor = %s"
        cursor.execute(sql, (self.numero_serie, self.fabricante, self.modelo, self.tipo_sensor, self.unidade_medida, self.protocolo_comunicacao, self.mac_address, self.endereco_ip, self.token_autenticacao, self.status_conexao, self.data_instalacao, self.data_ultima_calibracao, self.status, self.id_maquina, self.id_sensor))
        conexao.commit()
        cursor.close()
        conexao.close()

    def deletar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM sensor WHERE id_sensor = %s", (self.id_sensor,))
        conexao.commit()
        cursor.close()
        conexao.close()

    def __repr__(self):
        return f"<Sensor id_sensor={self.id_sensor}>"