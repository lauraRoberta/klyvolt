# -*- coding: utf-8 -*-
# Arquivo: src/GestaoEnergia/Models/Model.py

from GestaoEnergia.Database.Connection import Connection
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2 import sql


class Model:
    """
    Classe base abstrata para todos os modelos
    Equivalente ao Model.php do PHP
    """
    
    def __init__(self):
        """
        Inicializa o modelo com a conexão do banco
        """
        self.db = Connection.get_instance().get_connection()
        self.table = ''  # Deve ser sobrescrito nas classes filhas
        self.primary_key = 'id'  # PostgreSQL usa minúsculas por padrão
    
    def get_cursor(self):
        """
        Retorna um cursor para executar consultas
        
        Returns:
            cursor: Cursor do PostgreSQL
        """
        return self.db.cursor()
    
    def find_all(self) -> List[Dict[str, Any]]:
        """
        Busca todos os registros da tabela
        
        Returns:
            list: Lista de dicionários com todos os registros
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("SELECT * FROM {}").format(
                sql.Identifier(self.table)
            )
            cursor.execute(query)
            resultados = cursor.fetchall()
            cursor.close()
            
            # Converte para lista de dicionários
            registros = []
            for row in resultados:
                registros.append(self._row_to_dict(row, cursor))
            return registros
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar todos: {e}")
            cursor.close()
            return []
    
    def find_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """
        Busca um registro pelo ID
        
        Args:
            id (int): ID do registro
        
        Returns:
            dict: Dados do registro ou None
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("SELECT * FROM {} WHERE {} = %s").format(
                sql.Identifier(self.table),
                sql.Identifier(self.primary_key)
            )
            cursor.execute(query, (id,))
            resultado = cursor.fetchone()
            cursor.close()
            
            if resultado:
                return self._row_to_dict(resultado, cursor)
            return None
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar por ID: {e}")
            cursor.close()
            return None
    
    def create(self, data: Dict[str, Any]) -> int:
        """
        Cria um novo registro
        
        Args:
            data (dict): Dados a serem inseridos
        
        Returns:
            int: ID do registro criado
        """
        cursor = self.db.cursor()
        try:
            fields = list(data.keys())
            placeholders = ['%s'] * len(fields)
            
            query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING {}").format(
                sql.Identifier(self.table),
                sql.SQL(', ').join([sql.Identifier(f) for f in fields]),
                sql.SQL(', ').join(placeholders),
                sql.Identifier(self.primary_key)
            )
            
            cursor.execute(query, list(data.values()))
            id_criado = cursor.fetchone()[0]
            self.db.commit()
            cursor.close()
            return id_criado
            
        except psycopg2.Error as e:
            self.db.rollback()
            cursor.close()
            raise Exception(f"Erro ao criar registro: {e}")
    
    def update(self, id: int, data: Dict[str, Any]) -> bool:
        """
        Atualiza um registro existente
        
        Args:
            id (int): ID do registro a ser atualizado
            data (dict): Dados a serem atualizados
        
        Returns:
            bool: True se atualizou com sucesso
        """
        cursor = self.db.cursor()
        try:
            # Monta a cláusula SET
            set_clause = sql.SQL(', ').join([
                sql.SQL("{} = %s").format(sql.Identifier(field))
                for field in data.keys()
            ])
            
            query = sql.SQL("UPDATE {} SET {} WHERE {} = %s").format(
                sql.Identifier(self.table),
                set_clause,
                sql.Identifier(self.primary_key)
            )
            
            # Parâmetros: valores + ID
            params = list(data.values()) + [id]
            cursor.execute(query, params)
            
            # Verifica se alguma linha foi afetada
            linhas_afetadas = cursor.rowcount
            
            self.db.commit()
            cursor.close()
            return linhas_afetadas > 0
            
        except psycopg2.Error as e:
            self.db.rollback()
            cursor.close()
            print(f"Erro ao atualizar registro: {e}")
            return False
    
    def delete(self, id: int) -> bool:
        """
        Deleta um registro
        
        Args:
            id (int): ID do registro a ser deletado
        
        Returns:
            bool: True se deletou com sucesso
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("DELETE FROM {} WHERE {} = %s").format(
                sql.Identifier(self.table),
                sql.Identifier(self.primary_key)
            )
            cursor.execute(query, (id,))
            
            # Verifica se alguma linha foi afetada
            linhas_afetadas = cursor.rowcount
            
            self.db.commit()
            cursor.close()
            return linhas_afetadas > 0
            
        except psycopg2.Error as e:
            self.db.rollback()
            cursor.close()
            print(f"Erro ao deletar registro: {e}")
            return False
    
    def find_by(self, column: str, value: Any) -> List[Dict[str, Any]]:
        """
        Busca registros por uma coluna específica
        
        Args:
            column (str): Nome da coluna
            value (any): Valor a ser buscado
        
        Returns:
            list: Lista de registros encontrados
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("SELECT * FROM {} WHERE {} = %s").format(
                sql.Identifier(self.table),
                sql.Identifier(column)
            )
            cursor.execute(query, (value,))
            resultados = cursor.fetchall()
            cursor.close()
            
            registros = []
            for row in resultados:
                registros.append(self._row_to_dict(row, cursor))
            return registros
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar por {column}: {e}")
            cursor.close()
            return []
    
    def find_by_like(self, column: str, value: str) -> List[Dict[str, Any]]:
        """
        Busca registros usando LIKE
        
        Args:
            column (str): Nome da coluna
            value (str): Valor a ser buscado
        
        Returns:
            list: Lista de registros encontrados
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("SELECT * FROM {} WHERE {} LIKE %s").format(
                sql.Identifier(self.table),
                sql.Identifier(column)
            )
            cursor.execute(query, (f"%{value}%",))
            resultados = cursor.fetchall()
            cursor.close()
            
            registros = []
            for row in resultados:
                registros.append(self._row_to_dict(row, cursor))
            return registros
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar por LIKE: {e}")
            cursor.close()
            return []
    
    def find_by_field(self, column: str, value: Any, order_by: Optional[str] = None, 
                      limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Busca registros com opções adicionais
        
        Args:
            column (str): Nome da coluna
            value (any): Valor a ser buscado
            order_by (str, optional): Coluna para ordenação
            limit (int, optional): Limite de registros
        
        Returns:
            list: Lista de registros encontrados
        """
        cursor = self.db.cursor()
        try:
            query_parts = [
                sql.SQL("SELECT * FROM {} WHERE {} = %s").format(
                    sql.Identifier(self.table),
                    sql.Identifier(column)
                )
            ]
            
            if order_by:
                query_parts.append(sql.SQL("ORDER BY {}").format(
                    sql.Identifier(order_by)
                ))
            
            if limit:
                query_parts.append(sql.SQL("LIMIT %s"))
            
            query = sql.SQL(' ').join(query_parts)
            
            params = [value]
            if limit:
                params.append(limit)
            
            cursor.execute(query, params)
            resultados = cursor.fetchall()
            cursor.close()
            
            registros = []
            for row in resultados:
                registros.append(self._row_to_dict(row, cursor))
            return registros
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar por {column}: {e}")
            cursor.close()
            return []
    
    def count(self) -> int:
        """
        Conta o número total de registros
        
        Returns:
            int: Número total de registros
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("SELECT COUNT(*) FROM {}").format(
                sql.Identifier(self.table)
            )
            cursor.execute(query)
            total = cursor.fetchone()[0]
            cursor.close()
            return total
            
        except psycopg2.Error as e:
            print(f"Erro ao contar registros: {e}")
            cursor.close()
            return 0
    
    def count_by(self, column: str, value: Any) -> int:
        """
        Conta registros com uma condição específica
        
        Args:
            column (str): Nome da coluna
            value (any): Valor a ser contado
        
        Returns:
            int: Número de registros encontrados
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("SELECT COUNT(*) FROM {} WHERE {} = %s").format(
                sql.Identifier(self.table),
                sql.Identifier(column)
            )
            cursor.execute(query, (value,))
            total = cursor.fetchone()[0]
            cursor.close()
            return total
            
        except psycopg2.Error as e:
            print(f"Erro ao contar registros por {column}: {e}")
            cursor.close()
            return 0
    
    def exists(self, id: int) -> bool:
        """
        Verifica se um registro existe pelo ID
        
        Args:
            id (int): ID do registro
        
        Returns:
            bool: True se o registro existe
        """
        return self.count_by(self.primary_key, id) > 0
    
    def _row_to_dict(self, row, cursor) -> Dict[str, Any]:
        """
        Converte uma linha de resultado para dicionário
        
        Args:
            row: Tupla com os dados
            cursor: Cursor usado na consulta
        
        Returns:
            dict: Dados em formato de dicionário
        """
        # Obtém os nomes das colunas do cursor
        col_names = [desc[0] for desc in cursor.description]
        return dict(zip(col_names, row))
    
    def begin_transaction(self):
        """Inicia uma transação"""
        self.db.autocommit = False
    
    def commit(self):
        """Confirma a transação"""
        self.db.commit()
    
    def rollback(self):
        """Desfaz a transação"""
        self.db.rollback()
    
    def get_last_insert_id(self) -> int:
        """
        Obtém o último ID inserido (alternativa ao RETURNING)
        
        Returns:
            int: Último ID inserido
        """
        cursor = self.db.cursor()
        try:
            cursor.execute("SELECT LASTVAL()")
            last_id = cursor.fetchone()[0]
            cursor.close()
            return last_id
        except psycopg2.Error as e:
            cursor.close()
            return 0


# ============================================================
# EXEMPLO DE COMO USAR A CLASSE MODEL
# ============================================================
if __name__ == "__main__":
    """
    Exemplo de como criar um modelo específico usando a classe Model
    """
    
    # Definindo um modelo específico
    class Empresa(Model):
        def __init__(self):
            super().__init__()
            self.table = 'EMPRESA'
            self.primary_key = 'id_empresa'
        
        # Métodos específicos da classe
        def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
            """Busca uma empresa por email"""
            return self.find_by('email_empresa', email)
        
        def find_by_nome_like(self, nome: str) -> List[Dict[str, Any]]:
            """Busca empresas por nome (parcial)"""
            return self.find_by_like('nome_empresa', nome)
    
    try:
        # Testando o modelo
        empresa_model = Empresa()
        print("✅ Modelo Empresa inicializado com sucesso!")
        
        # Testar find_all
        print("\n📋 Listando empresas:")
        empresas = empresa_model.find_all()
        for empresa in empresas[:3]:  # Mostra apenas 3
            print(f"  - {empresa.get('nome_empresa', 'N/A')}")
        
        # Testar count
        total = empresa_model.count()
        print(f"\n📊 Total de empresas: {total}")
        
        # Testar find_by_id
        if total > 0:
            primeira = empresas[0]
            id_empresa = primeira.get('id_empresa')
            if id_empresa:
                empresa = empresa_model.find_by_id(id_empresa)
                if empresa:
                    print(f"\n🔍 Empresa encontrada: {empresa.get('nome_empresa')}")
        
        # Testar create (comentado para não criar dados duplicados)
        # novo_id = empresa_model.create({
        #     'nome_empresa': 'Empresa Teste',
        #     'email_empresa': 'teste@empresa.com'
        # })
        # print(f"\n✅ Nova empresa criada com ID: {novo_id}")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")# -*- coding: utf-8 -*-
# Arquivo: src/GestaoEnergia/Models/Model.py

from GestaoEnergia.Database.Connection import Connection
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2 import sql


class Model:
    """
    Classe base abstrata para todos os modelos
    Equivalente ao Model.php do PHP
    """
    
    def __init__(self):
        """
        Inicializa o modelo com a conexão do banco
        """
        self.db = Connection.get_instance().get_connection()
        self.table = ''  # Deve ser sobrescrito nas classes filhas
        self.primary_key = 'id'  # PostgreSQL usa minúsculas por padrão
    
    def get_cursor(self):
        """
        Retorna um cursor para executar consultas
        
        Returns:
            cursor: Cursor do PostgreSQL
        """
        return self.db.cursor()
    
    def find_all(self) -> List[Dict[str, Any]]:
        """
        Busca todos os registros da tabela
        
        Returns:
            list: Lista de dicionários com todos os registros
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("SELECT * FROM {}").format(
                sql.Identifier(self.table)
            )
            cursor.execute(query)
            resultados = cursor.fetchall()
            cursor.close()
            
            # Converte para lista de dicionários
            registros = []
            for row in resultados:
                registros.append(self._row_to_dict(row, cursor))
            return registros
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar todos: {e}")
            cursor.close()
            return []
    
    def find_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        """
        Busca um registro pelo ID
        
        Args:
            id (int): ID do registro
        
        Returns:
            dict: Dados do registro ou None
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("SELECT * FROM {} WHERE {} = %s").format(
                sql.Identifier(self.table),
                sql.Identifier(self.primary_key)
            )
            cursor.execute(query, (id,))
            resultado = cursor.fetchone()
            cursor.close()
            
            if resultado:
                return self._row_to_dict(resultado, cursor)
            return None
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar por ID: {e}")
            cursor.close()
            return None
    
    def create(self, data: Dict[str, Any]) -> int:
        """
        Cria um novo registro
        
        Args:
            data (dict): Dados a serem inseridos
        
        Returns:
            int: ID do registro criado
        """
        cursor = self.db.cursor()
        try:
            fields = list(data.keys())
            placeholders = ['%s'] * len(fields)
            
            query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING {}").format(
                sql.Identifier(self.table),
                sql.SQL(', ').join([sql.Identifier(f) for f in fields]),
                sql.SQL(', ').join(placeholders),
                sql.Identifier(self.primary_key)
            )
            
            cursor.execute(query, list(data.values()))
            id_criado = cursor.fetchone()[0]
            self.db.commit()
            cursor.close()
            return id_criado
            
        except psycopg2.Error as e:
            self.db.rollback()
            cursor.close()
            raise Exception(f"Erro ao criar registro: {e}")
    
    def update(self, id: int, data: Dict[str, Any]) -> bool:
        """
        Atualiza um registro existente
        
        Args:
            id (int): ID do registro a ser atualizado
            data (dict): Dados a serem atualizados
        
        Returns:
            bool: True se atualizou com sucesso
        """
        cursor = self.db.cursor()
        try:
            # Monta a cláusula SET
            set_clause = sql.SQL(', ').join([
                sql.SQL("{} = %s").format(sql.Identifier(field))
                for field in data.keys()
            ])
            
            query = sql.SQL("UPDATE {} SET {} WHERE {} = %s").format(
                sql.Identifier(self.table),
                set_clause,
                sql.Identifier(self.primary_key)
            )
            
            # Parâmetros: valores + ID
            params = list(data.values()) + [id]
            cursor.execute(query, params)
            
            # Verifica se alguma linha foi afetada
            linhas_afetadas = cursor.rowcount
            
            self.db.commit()
            cursor.close()
            return linhas_afetadas > 0
            
        except psycopg2.Error as e:
            self.db.rollback()
            cursor.close()
            print(f"Erro ao atualizar registro: {e}")
            return False
    
    def delete(self, id: int) -> bool:
        """
        Deleta um registro
        
        Args:
            id (int): ID do registro a ser deletado
        
        Returns:
            bool: True se deletou com sucesso
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("DELETE FROM {} WHERE {} = %s").format(
                sql.Identifier(self.table),
                sql.Identifier(self.primary_key)
            )
            cursor.execute(query, (id,))
            
            # Verifica se alguma linha foi afetada
            linhas_afetadas = cursor.rowcount
            
            self.db.commit()
            cursor.close()
            return linhas_afetadas > 0
            
        except psycopg2.Error as e:
            self.db.rollback()
            cursor.close()
            print(f"Erro ao deletar registro: {e}")
            return False
    
    def find_by(self, column: str, value: Any) -> List[Dict[str, Any]]:
        """
        Busca registros por uma coluna específica
        
        Args:
            column (str): Nome da coluna
            value (any): Valor a ser buscado
        
        Returns:
            list: Lista de registros encontrados
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("SELECT * FROM {} WHERE {} = %s").format(
                sql.Identifier(self.table),
                sql.Identifier(column)
            )
            cursor.execute(query, (value,))
            resultados = cursor.fetchall()
            cursor.close()
            
            registros = []
            for row in resultados:
                registros.append(self._row_to_dict(row, cursor))
            return registros
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar por {column}: {e}")
            cursor.close()
            return []
    
    def find_by_like(self, column: str, value: str) -> List[Dict[str, Any]]:
        """
        Busca registros usando LIKE
        
        Args:
            column (str): Nome da coluna
            value (str): Valor a ser buscado
        
        Returns:
            list: Lista de registros encontrados
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("SELECT * FROM {} WHERE {} LIKE %s").format(
                sql.Identifier(self.table),
                sql.Identifier(column)
            )
            cursor.execute(query, (f"%{value}%",))
            resultados = cursor.fetchall()
            cursor.close()
            
            registros = []
            for row in resultados:
                registros.append(self._row_to_dict(row, cursor))
            return registros
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar por LIKE: {e}")
            cursor.close()
            return []
    
    def find_by_field(self, column: str, value: Any, order_by: Optional[str] = None, 
                      limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Busca registros com opções adicionais
        
        Args:
            column (str): Nome da coluna
            value (any): Valor a ser buscado
            order_by (str, optional): Coluna para ordenação
            limit (int, optional): Limite de registros
        
        Returns:
            list: Lista de registros encontrados
        """
        cursor = self.db.cursor()
        try:
            query_parts = [
                sql.SQL("SELECT * FROM {} WHERE {} = %s").format(
                    sql.Identifier(self.table),
                    sql.Identifier(column)
                )
            ]
            
            if order_by:
                query_parts.append(sql.SQL("ORDER BY {}").format(
                    sql.Identifier(order_by)
                ))
            
            if limit:
                query_parts.append(sql.SQL("LIMIT %s"))
            
            query = sql.SQL(' ').join(query_parts)
            
            params = [value]
            if limit:
                params.append(limit)
            
            cursor.execute(query, params)
            resultados = cursor.fetchall()
            cursor.close()
            
            registros = []
            for row in resultados:
                registros.append(self._row_to_dict(row, cursor))
            return registros
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar por {column}: {e}")
            cursor.close()
            return []
    
    def count(self) -> int:
        """
        Conta o número total de registros
        
        Returns:
            int: Número total de registros
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("SELECT COUNT(*) FROM {}").format(
                sql.Identifier(self.table)
            )
            cursor.execute(query)
            total = cursor.fetchone()[0]
            cursor.close()
            return total
            
        except psycopg2.Error as e:
            print(f"Erro ao contar registros: {e}")
            cursor.close()
            return 0
    
    def count_by(self, column: str, value: Any) -> int:
        """
        Conta registros com uma condição específica
        
        Args:
            column (str): Nome da coluna
            value (any): Valor a ser contado
        
        Returns:
            int: Número de registros encontrados
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("SELECT COUNT(*) FROM {} WHERE {} = %s").format(
                sql.Identifier(self.table),
                sql.Identifier(column)
            )
            cursor.execute(query, (value,))
            total = cursor.fetchone()[0]
            cursor.close()
            return total
            
        except psycopg2.Error as e:
            print(f"Erro ao contar registros por {column}: {e}")
            cursor.close()
            return 0
    
    def exists(self, id: int) -> bool:
        """
        Verifica se um registro existe pelo ID
        
        Args:
            id (int): ID do registro
        
        Returns:
            bool: True se o registro existe
        """
        return self.count_by(self.primary_key, id) > 0
    
    def _row_to_dict(self, row, cursor) -> Dict[str, Any]:
        """
        Converte uma linha de resultado para dicionário
        
        Args:
            row: Tupla com os dados
            cursor: Cursor usado na consulta
        
        Returns:
            dict: Dados em formato de dicionário
        """
        # Obtém os nomes das colunas do cursor
        col_names = [desc[0] for desc in cursor.description]
        return dict(zip(col_names, row))
    
    def begin_transaction(self):
        """Inicia uma transação"""
        self.db.autocommit = False
    
    def commit(self):
        """Confirma a transação"""
        self.db.commit()
    
    def rollback(self):
        """Desfaz a transação"""
        self.db.rollback()
    
    def get_last_insert_id(self) -> int:
        """
        Obtém o último ID inserido (alternativa ao RETURNING)
        
        Returns:
            int: Último ID inserido
        """
        cursor = self.db.cursor()
        try:
            cursor.execute("SELECT LASTVAL()")
            last_id = cursor.fetchone()[0]
            cursor.close()
            return last_id
        except psycopg2.Error as e:
            cursor.close()
            return 0


# ============================================================
# EXEMPLO DE COMO USAR A CLASSE MODEL
# ============================================================
if __name__ == "__main__":
    """
    Exemplo de como criar um modelo específico usando a classe Model
    """
    
    # Definindo um modelo específico
    class Empresa(Model):
        def __init__(self):
            super().__init__()
            self.table = 'EMPRESA'
            self.primary_key = 'id_empresa'
        
        # Métodos específicos da classe
        def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
            """Busca uma empresa por email"""
            return self.find_by('email_empresa', email)
        
        def find_by_nome_like(self, nome: str) -> List[Dict[str, Any]]:
            """Busca empresas por nome (parcial)"""
            return self.find_by_like('nome_empresa', nome)
    
    try:
        # Testando o modelo
        empresa_model = Empresa()
        print("✅ Modelo Empresa inicializado com sucesso!")
        
        # Testar find_all
        print("\n📋 Listando empresas:")
        empresas = empresa_model.find_all()
        for empresa in empresas[:3]:  # Mostra apenas 3
            print(f"  - {empresa.get('nome_empresa', 'N/A')}")
        
        # Testar count
        total = empresa_model.count()
        print(f"\n📊 Total de empresas: {total}")
        
        # Testar find_by_id
        if total > 0:
            primeira = empresas[0]
            id_empresa = primeira.get('id_empresa')
            if id_empresa:
                empresa = empresa_model.find_by_id(id_empresa)
                if empresa:
                    print(f"\n🔍 Empresa encontrada: {empresa.get('nome_empresa')}")
        
        # Testar create (comentado para não criar dados duplicados)
        # novo_id = empresa_model.create({
        #     'nome_empresa': 'Empresa Teste',
        #     'email_empresa': 'teste@empresa.com'
        # })
        # print(f"\n✅ Nova empresa criada com ID: {novo_id}")
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")