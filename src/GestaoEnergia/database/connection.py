# -*- coding: utf-8 -*-
# Arquivo: src/GestaoEnergia/Database/Connection.py

import psycopg2
from psycopg2 import sql, extras
from psycopg2.extensions import connection as PgConnection
import os
from typing import Optional


class Connection:
    """Singleton para gerenciar a conexão com o PostgreSQL"""
    
    _instance: Optional['Connection'] = None
    
    def __new__(cls):
        """Implementação do padrão Singleton"""
        if cls._instance is None:
            cls._instance = super(Connection, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inicializa a conexão com o banco de dados"""
        # Evita reinicialização
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        # CONFIGURAÇÃO PARA POSTGRESQL
        # Pode ser configurado via variáveis de ambiente para maior segurança
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = os.getenv('DB_PORT', '5432')
        self.dbname = os.getenv('DB_NAME', 'gestao_energetica')
        self.user = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', '')  # Coloque sua senha aqui se tiver
        
        # DSN para PostgreSQL
        self.dsn = f"host={self.host} port={self.port} dbname={self.dbname} user={self.user} password={self.password}"
        
        try:
            # Estabelece a conexão
            self._conn = psycopg2.connect(self.dsn)
            
            # Configura o modo de busca para retornar dicionários
            # Isso é equivalente ao PDO::FETCH_ASSOC do PHP
            self._conn.cursor_factory = extras.RealDictCursor
            
            # Auto-commit pode ser configurado conforme necessidade
            # Por padrão, o psycopg2 não faz auto-commit
            self._conn.autocommit = False
            
            self._initialized = True
            
        except psycopg2.Error as e:
            print(f"Erro ao conectar ao PostgreSQL: {e}")
            raise  # Re-lança a exceção para ser tratada pelo código que chama
    
    @classmethod
    def get_instance(cls) -> 'Connection':
        """
        Retorna a instância única da conexão (Singleton)
        
        Returns:
            Connection: Instância da conexão
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def get_connection(self) -> PgConnection:
        """
        Retorna o objeto de conexão PDO equivalente
        
        Returns:
            PgConnection: Conexão com o PostgreSQL
        """
        return self._conn
    
    def get_cursor(self):
        """
        Retorna um cursor para executar consultas
        
        Returns:
            cursor: Cursor configurado para retornar dicionários
        """
        return self._conn.cursor()
    
    def close(self):
        """Fecha a conexão com o banco de dados"""
        if hasattr(self, '_conn') and self._conn:
            self._conn.close()
            self._initialized = False
    
    def begin_transaction(self):
        """Inicia uma transação"""
        if hasattr(self, '_conn') and self._conn:
            self._conn.autocommit = False
    
    def commit(self):
        """Confirma a transação atual"""
        if hasattr(self, '_conn') and self._conn:
            self._conn.commit()
    
    def rollback(self):
        """Desfaz a transação atual"""
        if hasattr(self, '_conn') and self._conn:
            self._conn.rollback()
    
    def __enter__(self):
        """Suporte para context manager (with)"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Fecha a conexão ao sair do context manager"""
        self.close()


# ============================================================
# EXEMPLO DE USO
# ============================================================
if __name__ == "__main__":
    # Exemplo de como usar a classe
    
    # 1. Usando o padrão Singleton
    print("=== Usando Singleton ===")
    db1 = Connection.get_instance()
    db2 = Connection.get_instance()
    print(f"db1 é db2? {db1 is db2}")  # True - mesma instância
    
    # 2. Obtendo a conexão
    conn = db1.get_connection()
    print(f"Conexão estabelecida: {conn}")
    
    # 3. Executando uma consulta
    cursor = db1.get_cursor()
    cursor.execute("SELECT version()")
    version = cursor.fetchone()
    print(f"Versão do PostgreSQL: {version['version']}")
    cursor.close()
    
    # 4. Usando com context manager
    print("\n=== Usando context manager ===")
    with Connection.get_instance() as db:
        cursor = db.get_cursor()
        cursor.execute("SELECT NOW() as current_time")
        result = cursor.fetchone()
        print(f"Hora atual: {result['current_time']}")
        cursor.close()
    
    # 5. Exemplo de transação
    print("\n=== Exemplo de transação ===")
    db = Connection.get_instance()
    try:
        db.begin_transaction()
        cursor = db.get_cursor()
        
        # Simula operações de banco de dados
        cursor.execute("SELECT COUNT(*) as total FROM EMPRESA")
        total = cursor.fetchone()
        print(f"Total de empresas: {total['total']}")
        
        # Commit da transação
        db.commit()
        print("Transação concluída com sucesso!")
        cursor.close()
        
    except Exception as e:
        db.rollback()
        print(f"Erro na transação, rollback executado: {e}")
    
    # Fecha a conexão
    db.close()
    print("\nConexão fechada.")