"""
Modelo da tabela `empresa` - Klyvolt (PostgreSQL)
Gerado a partir do DER final do projeto (schema revisado).
"""

import psycopg2.extras
from conexao import conectar


class Empresa:
    def __init__(self, id_empresa=None, cnpj=None, nome_empresa=None, email_empresa=None, senha_empresa=None, telefone_empresa=None):
        self.id_empresa = id_empresa
        self.cnpj = cnpj
        self.nome_empresa = nome_empresa
        self.email_empresa = email_empresa
        self.senha_empresa = senha_empresa
        self.telefone_empresa = telefone_empresa

    @staticmethod
    def criar(cnpj, nome_empresa, email_empresa, senha_empresa, telefone_empresa):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "INSERT INTO empresa (cnpj, nome_empresa, email_empresa, senha_empresa, telefone_empresa) VALUES (%s, %s, %s, %s, %s) RETURNING id_empresa"
        cursor.execute(sql, (cnpj, nome_empresa, email_empresa, senha_empresa, telefone_empresa))
        novo_id = cursor.fetchone()[0]
        conexao.commit()
        cursor.close()
        conexao.close()
    @staticmethod
    def buscar_por_id(id_valor):
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM empresa WHERE id_empresa = %s", (id_valor,))
        resultado = cursor.fetchone()
        cursor.close()
        conexao.close()
        if resultado:
            return Empresa(**resultado)
        return None

    @staticmethod
    def listar_todos():
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM empresa")
        resultados = cursor.fetchall()
        cursor.close()
        conexao.close()
        return [Empresa(**linha) for linha in resultados]

    def atualizar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "UPDATE empresa SET cnpj = %s, nome_empresa = %s, email_empresa = %s, senha_empresa = %s, telefone_empresa = %s WHERE id_empresa = %s"
        cursor.execute(sql, (self.cnpj, self.nome_empresa, self.email_empresa, self.senha_empresa, self.telefone_empresa, self.id_empresa))
        conexao.commit()
        cursor.close()
        conexao.close()

    def deletar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM empresa WHERE id_empresa = %s", (self.id_empresa,))
        conexao.commit()
        cursor.close()
        conexao.close()

    def __repr__(self):
        return f"<Empresa id_empresa={self.id_empresa}>"
