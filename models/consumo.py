# -*- coding: utf-8 -*-
# Arquivo: src/GestaoEnergia/Models/Consumo.py

from GestaoEnergia.Models.Model import Model
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2 import sql


class Consumo(Model):
    """
    Modelo para gerenciar registros de consumo de energia
    """
    
    def __init__(self):
        """
        Inicializa o modelo Consumo
        """
        super().__init__()
        self.table = 'CONSUMO'
        self.primary_key = 'id_consumo'  # PostgreSQL usa minúsculas
    
    def criar_consumo(
        self,
        data_inicio: str,
        data_fim: str,
        consumo_kwh: float,
        id_maquina: int,
        id_leitura_inicial: int,
        id_leitura_final: int
    ) -> int:
        """
        Cria um novo registro de consumo
        
        Args:
            data_inicio (str): Data de início (formato YYYY-MM-DD HH:MM:SS)
            data_fim (str): Data de fim (formato YYYY-MM-DD HH:MM:SS)
            consumo_kwh (float): Consumo em kWh
            id_maquina (int): ID da máquina
            id_leitura_inicial (int): ID da leitura inicial
            id_leitura_final (int): ID da leitura final
        
        Returns:
            int: ID do consumo criado
        """
        # Mapeamento dos campos do banco (em minúsculo para PostgreSQL)
        dados = {
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'consumo_kwh': consumo_kwh,
            'id_maquina': id_maquina,
            'id_leitura_inicial': id_leitura_inicial,
            'id_leitura_final': id_leitura_final
        }
        
        return self.create(dados)
    
    def find_by_maquina(self, id_maquina: int) -> List[Dict[str, Any]]:
        """
        Busca todos os consumos de uma máquina específica
        
        Args:
            id_maquina (int): ID da máquina
        
        Returns:
            list: Lista de dicionários com os consumos encontrados
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT * FROM {} 
                WHERE id_maquina = %s 
                ORDER BY data_fim DESC
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_maquina,))
            resultados = cursor.fetchall()
            cursor.close()
            
            # Converte para lista de dicionários
            consumos = []
            for row in resultados:
                consumos.append(self._row_to_dict(row, cursor))
            return consumos
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar consumos por máquina: {e}")
            cursor.close()
            return []
    
    def find_by_periodo(self, id_maquina: int, data_inicio: str, data_fim: str) -> List[Dict[str, Any]]:
        """
        Busca consumos de uma máquina em um período específico
        
        Args:
            id_maquina (int): ID da máquina
            data_inicio (str): Data de início
            data_fim (str): Data de fim
        
        Returns:
            list: Lista de consumos no período
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT * FROM {} 
                WHERE id_maquina = %s 
                AND data_inicio >= %s 
                AND data_fim <= %s
                ORDER BY data_inicio
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_maquina, data_inicio, data_fim))
            resultados = cursor.fetchall()
            cursor.close()
            
            consumos = []
            for row in resultados:
                consumos.append(self._row_to_dict(row, cursor))
            return consumos
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar consumos por período: {e}")
            cursor.close()
            return []
    
    def get_total_consumo_by_maquina(self, id_maquina: int) -> float:
        """
        Calcula o consumo total de uma máquina
        
        Args:
            id_maquina (int): ID da máquina
        
        Returns:
            float: Consumo total em kWh
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT SUM(consumo_kwh) as total
                FROM {} 
                WHERE id_maquina = %s
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_maquina,))
            resultado = cursor.fetchone()
            cursor.close()
            
            total = resultado[0] if resultado[0] is not None else 0.0
            return float(total)
            
        except psycopg2.Error as e:
            print(f"Erro ao calcular consumo total: {e}")
            cursor.close()
            return 0.0
    
    def get_consumo_medio_diario(self, id_maquina: int, dias: int = 30) -> float:
        """
        Calcula o consumo médio diário dos últimos N dias
        
        Args:
            id_maquina (int): ID da máquina
            dias (int): Número de dias para calcular a média
        
        Returns:
            float: Consumo médio diário em kWh
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT AVG(consumo_kwh) as media
                FROM {} 
                WHERE id_maquina = %s 
                AND data_fim >= NOW() - INTERVAL '%s days'
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_maquina, dias))
            resultado = cursor.fetchone()
            cursor.close()
            
            media = resultado[0] if resultado[0] is not None else 0.0
            return float(media)
            
        except psycopg2.Error as e:
            print(f"Erro ao calcular consumo médio: {e}")
            cursor.close()
            return 0.0
    
    def get_consumo_por_mes(self, id_maquina: int, ano: int, mes: int) -> float:
        """
        Calcula o consumo total de uma máquina em um mês específico
        
        Args:
            id_maquina (int): ID da máquina
            ano (int): Ano
            mes (int): Mês (1-12)
        
        Returns:
            float: Consumo total do mês em kWh
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT SUM(consumo_kwh) as total
                FROM {} 
                WHERE id_maquina = %s 
                AND EXTRACT(YEAR FROM data_fim) = %s
                AND EXTRACT(MONTH FROM data_fim) = %s
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_maquina, ano, mes))
            resultado = cursor.fetchone()
            cursor.close()
            
            total = resultado[0] if resultado[0] is not None else 0.0
            return float(total)
            
        except psycopg2.Error as e:
            print(f"Erro ao calcular consumo por mês: {e}")
            cursor.close()
            return 0.0
    
    def get_ultimos_consumos(self, id_maquina: int, limite: int = 10) -> List[Dict[str, Any]]:
        """
        Busca os últimos consumos de uma máquina
        
        Args:
            id_maquina (int): ID da máquina
            limite (int): Número máximo de registros
        
        Returns:
            list: Lista dos últimos consumos
        """
        return self.find_by_maquina(id_maquina)[:limite]
    
    def calcular_consumo_total_periodo(self, id_maquina: int, data_inicio: str, data_fim: str) -> float:
        """
        Calcula o consumo total de uma máquina em um período
        
        Args:
            id_maquina (int): ID da máquina
            data_inicio (str): Data de início
            data_fim (str): Data de fim
        
        Returns:
            float: Consumo total no período em kWh
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT SUM(consumo_kwh) as total
                FROM {} 
                WHERE id_maquina = %s 
                AND data_inicio >= %s 
                AND data_fim <= %s
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_maquina, data_inicio, data_fim))
            resultado = cursor.fetchone()
            cursor.close()
            
            total = resultado[0] if resultado[0] is not None else 0.0
            return float(total)
            
        except psycopg2.Error as e:
            print(f"Erro ao calcular consumo total do período: {e}")
            cursor.close()
            return 0.0


# ============================================================
# EXEMPLO DE USO
# ============================================================
if __name__ == "__main__":
    try:
        # Instancia o modelo
        consumo_model = Consumo()
        print("✅ Modelo Consumo inicializado com sucesso!")
        
        # Exemplo: Criar um consumo
        novo_id = consumo_model.criar_consumo(
            data_inicio='2026-08-20 08:00:00',
            data_fim='2026-08-20 10:00:00',
            consumo_kwh=150.5,
            id_maquina=1,
            id_leitura_inicial=1,
            id_leitura_final=2
        )
        print(f"✅ Consumo criado com ID: {novo_id}")
        
        # Exemplo: Buscar consumos de uma máquina
        consumos = consumo_model.find_by_maquina(1)
        print(f"\n📊 Consumos da máquina 1: {len(consumos)} registros")
        for consumo in consumos[:3]:  # Mostra apenas 3
            print(f"  - ID: {consumo['id_consumo']}, kWh: {consumo['consumo_kwh']}")
        
        # Exemplo: Calcular consumo total
        total = consumo_model.get_total_consumo_by_maquina(1)
        print(f"\n📈 Consumo total da máquina 1: {total:.2f} kWh")
        
        # Exemplo: Média diária
        media = consumo_model.get_consumo_medio_diario(1, 30)
        print(f"📈 Média diária (30 dias): {media:.2f} kWh")
        
    except Exception as e:
        print(f"❌ Erro: {e}")