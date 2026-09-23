"""
Modelo da tabela `usuario` - Klyvolt (PostgreSQL)
Gerado a partir do DER final do projeto (schema revisado).
"""

import psycopg2.extras
from src.database.conexao import conectar


class Usuario:
    def __init__(self, id_usuario=None, nome_usuario=None, email_usuario=None, senha_usuario=None, tipo_usuario=None, id_empresa=None):
        self.id_usuario = id_usuario
        self.nome_usuario = nome_usuario
        self.email_usuario = email_usuario
        self.senha_usuario = senha_usuario
        self.tipo_usuario = tipo_usuario
        self.id_empresa = id_empresa

    @staticmethod
    def criar(nome_usuario, email_usuario, senha_usuario, tipo_usuario, id_empresa):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "INSERT INTO usuario (nome_usuario, email_usuario, senha_usuario, tipo_usuario, id_empresa) VALUES (%s, %s, %s, %s, %s) RETURNING id_usuario"
        cursor.execute(sql, (nome_usuario, email_usuario, senha_usuario, tipo_usuario, id_empresa))
        novo_id = cursor.fetchone()[0]
        conexao.commit()
        cursor.close()
        conexao.close()
        return novo_id

    @staticmethod
    def buscar_por_id(id_valor):
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM usuario WHERE id_usuario = %s", (id_valor,))
        resultado = cursor.fetchone()
        cursor.close()
        conexao.close()
        if resultado:
            return Usuario(**resultado)
        return None

    @staticmethod
    def listar_todos():
        conexao = conectar()
        cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT * FROM usuario")
        resultados = cursor.fetchall()
        cursor.close()
        conexao.close()
        return [Usuario(**linha) for linha in resultados]

    def atualizar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        sql = "UPDATE usuario SET nome_usuario = %s, email_usuario = %s, senha_usuario = %s, tipo_usuario = %s, id_empresa = %s WHERE id_usuario = %s"
        cursor.execute(sql, (self.nome_usuario, self.email_usuario, self.senha_usuario, self.tipo_usuario, self.id_empresa, self.id_usuario))
        conexao.commit()
        cursor.close()
        conexao.close()

    def deletar(self):
        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM usuario WHERE id_usuario = %s", (self.id_usuario,))
        conexao.commit()
        cursor.close()
        conexao.close()

    def __repr__(self):
        return f"<Usuario id_usuario={self.id_usuario}>"
