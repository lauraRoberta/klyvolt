# -*- coding: utf-8 -*-
# Arquivo: src/GestaoEnergia/Models/Leitura.py

from GestaoEnergia.Models.Model import Model
from typing import List, Dict, Any, Optional
from datetime import datetime
import psycopg2
from psycopg2 import sql


class Leitura(Model):
    """
    Modelo para gerenciar registros de leituras de energia
    """
    
    def __init__(self):
        """
        Inicializa o modelo Leitura
        """
        super().__init__()
        self.table = 'LEITURA'
        self.primary_key = 'id_leitura'  # PostgreSQL usa minúsculas
    
    def find_by_maquina(self, id_maquina: int) -> List[Dict[str, Any]]:
        """
        Busca todas as leituras de uma máquina específica
        
        Args:
            id_maquina (int): ID da máquina
        
        Returns:
            list: Lista de dicionários com as leituras encontradas
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT * FROM {} 
                WHERE id_maquina = %s 
                ORDER BY data_leitura DESC
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_maquina,))
            resultados = cursor.fetchall()
            cursor.close()
            
            # Converte para lista de dicionários
            leituras = []
            for row in resultados:
                leituras.append(self._row_to_dict(row, cursor))
            return leituras
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar leituras por máquina: {e}")
            cursor.close()
            return []
    
    def find_last_by_maquina(self, id_maquina: int) -> Optional[Dict[str, Any]]:
        """
        Busca a última leitura de uma máquina específica
        
        Args:
            id_maquina (int): ID da máquina
        
        Returns:
            dict: Dados da última leitura ou None se não encontrada
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT * FROM {} 
                WHERE id_maquina = %s 
                ORDER BY id_leitura DESC 
                LIMIT 1
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_maquina,))
            resultado = cursor.fetchone()
            cursor.close()
            
            if resultado:
                return self._row_to_dict(resultado, cursor)
            return None
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar última leitura: {e}")
            cursor.close()
            return None
    
    def find_last_by_maquina_data(self, id_maquina: int) -> Optional[Dict[str, Any]]:
        """
        Busca a última leitura de uma máquina por data (alternativa)
        
        Args:
            id_maquina (int): ID da máquina
        
        Returns:
            dict: Dados da última leitura ou None
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT * FROM {} 
                WHERE id_maquina = %s 
                ORDER BY data_leitura DESC 
                LIMIT 1
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_maquina,))
            resultado = cursor.fetchone()
            cursor.close()
            
            if resultado:
                return self._row_to_dict(resultado, cursor)
            return None
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar última leitura por data: {e}")
            cursor.close()
            return None
    
    def registrar(
        self, 
        id_maquina: int, 
        id_usuario: int, 
        valor: float, 
        obs: Optional[str] = None
    ) -> int:
        """
        Registra uma nova leitura
        
        Args:
            id_maquina (int): ID da máquina
            id_usuario (int): ID do usuário que registrou
            valor (float): Valor medido em kWh
            obs (str, optional): Observação sobre a leitura
        
        Returns:
            int: ID da leitura criada
        """
        # Obtém a data/hora atual no formato PostgreSQL
        data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Mapeamento dos campos do banco (em minúsculo para PostgreSQL)
        dados = {
            'data_leitura': data_atual,
            'valor_medido_kwh': valor,
            'observacao_leitura': obs,
            'id_maquina': id_maquina,
            'id_usuario': id_usuario
        }
        
        return self.create(dados)
    
    def find_by_periodo(self, id_maquina: int, data_inicio: str, data_fim: str) -> List[Dict[str, Any]]:
        """
        Busca leituras de uma máquina em um período específico
        
        Args:
            id_maquina (int): ID da máquina
            data_inicio (str): Data de início (YYYY-MM-DD)
            data_fim (str): Data de fim (YYYY-MM-DD)
        
        Returns:
            list: Lista de leituras no período
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT * FROM {} 
                WHERE id_maquina = %s 
                AND data_leitura >= %s 
                AND data_leitura <= %s
                ORDER BY data_leitura DESC
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_maquina, data_inicio, data_fim))
            resultados = cursor.fetchall()
            cursor.close()
            
            leituras = []
            for row in resultados:
                leituras.append(self._row_to_dict(row, cursor))
            return leituras
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar leituras por período: {e}")
            cursor.close()
            return []
    
    def get_ultima_leitura_com_diferenca(self, id_maquina: int) -> Optional[Dict[str, Any]]:
        """
        Busca a última leitura e calcula a diferença para a penúltima
        
        Args:
            id_maquina (int): ID da máquina
        
        Returns:
            dict: Última leitura com diferença calculada
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                WITH ultimas_leituras AS (
                    SELECT 
                        id_leitura,
                        valor_medido_kwh,
                        data_leitura,
                        LAG(valor_medido_kwh) OVER (ORDER BY data_leitura DESC) as valor_anterior
                    FROM {} 
                    WHERE id_maquina = %s
                    ORDER BY data_leitura DESC
                    LIMIT 2
                )
                SELECT 
                    id_leitura,
                    valor_medido_kwh,
                    data_leitura,
                    valor_anterior,
                    (valor_medido_kwh - valor_anterior) as diferenca
                FROM ultimas_leituras
                ORDER BY data_leitura DESC
                LIMIT 1
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_maquina,))
            resultado = cursor.fetchone()
            cursor.close()
            
            if resultado:
                return {
                    'id_leitura': resultado[0],
                    'valor_medido_kwh': resultado[1],
                    'data_leitura': resultado[2],
                    'valor_anterior': resultado[3],
                    'diferenca': resultado[4] if resultado[4] is not None else 0.0
                }
            return None
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar última leitura com diferença: {e}")
            cursor.close()
            return None
    
    def get_leituras_com_nome_maquina(self, limite: int = 10) -> List[Dict[str, Any]]:
        """
        Busca leituras com o nome da máquina
        
        Args:
            limite (int): Número máximo de registros
        
        Returns:
            list: Lista de leituras com dados da máquina
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT 
                    l.id_leitura,
                    l.valor_medido_kwh,
                    l.data_leitura,
                    l.observacao_leitura,
                    m.nome_maquina,
                    m.descricao_maquina
                FROM {} l
                JOIN MAQUINA m ON l.id_maquina = m.id_maquina
                ORDER BY l.data_leitura DESC
                LIMIT %s
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (limite,))
            resultados = cursor.fetchall()
            cursor.close()
            
            leituras = []
            for row in resultados:
                leituras.append({
                    'id_leitura': row[0],
                    'valor_medido_kwh': row[1],
                    'data_leitura': row[2],
                    'observacao_leitura': row[3],
                    'nome_maquina': row[4],
                    'descricao_maquina': row[5]
                })
            return leituras
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar leituras com nome da máquina: {e}")
            cursor.close()
            return []
    
    def get_media_leituras(self, id_maquina: int, dias: int = 30) -> float:
        """
        Calcula a média das leituras dos últimos N dias
        
        Args:
            id_maquina (int): ID da máquina
            dias (int): Número de dias para calcular a média
        
        Returns:
            float: Média das leituras
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT AVG(valor_medido_kwh) as media
                FROM {} 
                WHERE id_maquina = %s 
                AND data_leitura >= NOW() - INTERVAL '%s days'
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_maquina, dias))
            resultado = cursor.fetchone()
            cursor.close()
            
            media = resultado[0] if resultado[0] is not None else 0.0
            return float(media)
            
        except psycopg2.Error as e:
            print(f"Erro ao calcular média de leituras: {e}")
            cursor.close()
            return 0.0
    
    def get_ultimas_leituras_by_maquina(self, id_maquina: int, limite: int = 5) -> List[Dict[str, Any]]:
        """
        Busca as últimas N leituras de uma máquina
        
        Args:
            id_maquina (int): ID da máquina
            limite (int): Número de leituras a retornar
        
        Returns:
            list: Lista das últimas leituras
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT * FROM {} 
                WHERE id_maquina = %s 
                ORDER BY data_leitura DESC 
                LIMIT %s
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_maquina, limite))
            resultados = cursor.fetchall()
            cursor.close()
            
            leituras = []
            for row in resultados:
                leituras.append(self._row_to_dict(row, cursor))
            return leituras
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar últimas leituras: {e}")
            cursor.close()
            return []
    
    def get_stats_maquina(self, id_maquina: int) -> Dict[str, Any]:
        """
        Obtém estatísticas das leituras de uma máquina
        
        Args:
            id_maquina (int): ID da máquina
        
        Returns:
            dict: Estatísticas (total, média, min, max, etc.)
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT 
                    COUNT(*) as total_leituras,
                    AVG(valor_medido_kwh) as media,
                    MIN(valor_medido_kwh) as minimo,
                    MAX(valor_medido_kwh) as maximo,
                    MAX(data_leitura) as ultima_leitura
                FROM {} 
                WHERE id_maquina = %s
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_maquina,))
            resultado = cursor.fetchone()
            cursor.close()
            
            if resultado:
                return {
                    'total_leituras': resultado[0],
                    'media': float(resultado[1]) if resultado[1] else 0.0,
                    'minimo': float(resultado[2]) if resultado[2] else 0.0,
                    'maximo': float(resultado[3]) if resultado[3] else 0.0,
                    'ultima_leitura': resultado[4]
                }
            return {
                'total_leituras': 0,
                'media': 0.0,
                'minimo': 0.0,
                'maximo': 0.0,
                'ultima_leitura': None
            }
            
        except psycopg2.Error as e:
            print(f"Erro ao obter estatísticas: {e}")
            cursor.close()
            return {
                'total_leituras': 0,
                'media': 0.0,
                'minimo': 0.0,
                'maximo': 0.0,
                'ultima_leitura': None
            }


# ============================================================
# EXEMPLO DE USO
# ============================================================
if __name__ == "__main__":
    try:
        # Instancia o modelo
        leitura_model = Leitura()
        print("✅ Modelo Leitura inicializado com sucesso!")
        
        # Exemplo 1: Registrar uma leitura
        novo_id = leitura_model.registrar(
            id_maquina=1,
            id_usuario=1,
            valor=150.5,
            obs="Leitura de rotina"
        )
        print(f"✅ Leitura criada com ID: {novo_id}")
        
        # Exemplo 2: Buscar leituras da máquina
        leituras = leitura_model.find_by_maquina(1)
        print(f"\n📊 Leituras da máquina 1: {len(leituras)} registros")
        for leitura in leituras[:3]:  # Mostra apenas 3
            print(f"  - ID: {leitura['id_leitura']}, Valor: {leitura['valor_medido_kwh']} kWh")
        
        # Exemplo 3: Buscar última leitura
        ultima = leitura_model.find_last_by_maquina(1)
        if ultima:
            print(f"\n📈 Última leitura da máquina 1:")
            print(f"  - ID: {ultima['id_leitura']}")
            print(f"  - Valor: {ultima['valor_medido_kwh']} kWh")
            print(f"  - Data: {ultima['data_leitura']}")
        
        # Exemplo 4: Estatísticas
        stats = leitura_model.get_stats_maquina(1)
        print(f"\n📊 Estatísticas da máquina 1:")
        print(f"  - Total de leituras: {stats['total_leituras']}")
        print(f"  - Média: {stats['media']:.2f} kWh")
        print(f"  - Mínimo: {stats['minimo']:.2f} kWh")
        print(f"  - Máximo: {stats['maximo']:.2f} kWh")
        
        # Exemplo 5: Buscar leituras com nome da máquina
        leituras_com_nome = leitura_model.get_leituras_com_nome_maquina(5)
        print(f"\n📋 Últimas 5 leituras com nome da máquina:")
        for leitura in leituras_com_nome:
            print(f"  - {leitura['nome_maquina']}: {leitura['valor_medido_kwh']} kWh")
        
    except Exception as e:
        print(f"❌ Erro: {e}")