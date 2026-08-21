# -*- coding: utf-8 -*-
# Arquivo: src/GestaoEnergia/Models/Custo.py

from GestaoEnergia.Models.Model import Model
from typing import List, Dict, Any, Optional
from datetime import datetime
import psycopg2
from psycopg2 import sql


class Custo(Model):
    """
    Modelo para gerenciar registros de custos de energia
    """
    
    def __init__(self):
        """
        Inicializa o modelo Custo
        """
        super().__init__()
        self.table = 'CUSTO'
        self.primary_key = 'id_custo'  # PostgreSQL usa minúsculas
    
    def calcular_custo(self, id_consumo: int, id_tarifa: int, valor_total: float) -> int:
        """
        Calcula e registra um novo custo
        
        Args:
            id_consumo (int): ID do consumo
            id_tarifa (int): ID da tarifa aplicada
            valor_total (float): Valor total do custo
        
        Returns:
            int: ID do custo criado
        """
        # Obtém a data/hora atual no formato PostgreSQL
        data_atual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Mapeamento dos campos do banco (em minúsculo para PostgreSQL)
        dados = {
            'data_calculo': data_atual,
            'valor_total': valor_total,
            'id_consumo': id_consumo,
            'id_tarifa': id_tarifa
        }
        
        return self.create(dados)
    
    def find_by_consumo(self, id_consumo: int) -> Optional[Dict[str, Any]]:
        """
        Busca o custo de um consumo específico
        
        Args:
            id_consumo (int): ID do consumo
        
        Returns:
            dict: Dados do custo ou None se não encontrado
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT * FROM {} 
                WHERE id_consumo = %s
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_consumo,))
            resultado = cursor.fetchone()
            cursor.close()
            
            if resultado:
                return self._row_to_dict(resultado, cursor)
            return None
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar custo por consumo: {e}")
            cursor.close()
            return None
    
    def find_by_tarifa(self, id_tarifa: int) -> List[Dict[str, Any]]:
        """
        Busca todos os custos de uma tarifa específica
        
        Args:
            id_tarifa (int): ID da tarifa
        
        Returns:
            list: Lista de custos encontrados
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT * FROM {} 
                WHERE id_tarifa = %s
                ORDER BY data_calculo DESC
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_tarifa,))
            resultados = cursor.fetchall()
            cursor.close()
            
            custos = []
            for row in resultados:
                custos.append(self._row_to_dict(row, cursor))
            return custos
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar custos por tarifa: {e}")
            cursor.close()
            return []
    
    def find_by_periodo(self, data_inicio: str, data_fim: str) -> List[Dict[str, Any]]:
        """
        Busca custos em um período específico
        
        Args:
            data_inicio (str): Data de início (YYYY-MM-DD)
            data_fim (str): Data de fim (YYYY-MM-DD)
        
        Returns:
            list: Lista de custos no período
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT * FROM {} 
                WHERE data_calculo >= %s 
                AND data_calculo <= %s
                ORDER BY data_calculo DESC
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (data_inicio, data_fim))
            resultados = cursor.fetchall()
            cursor.close()
            
            custos = []
            for row in resultados:
                custos.append(self._row_to_dict(row, cursor))
            return custos
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar custos por período: {e}")
            cursor.close()
            return []
    
    def get_total_custo_by_consumo(self, id_consumo: int) -> float:
        """
        Obtém o valor total de custo de um consumo específico
        
        Args:
            id_consumo (int): ID do consumo
        
        Returns:
            float: Valor total do custo
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT valor_total
                FROM {} 
                WHERE id_consumo = %s
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_consumo,))
            resultado = cursor.fetchone()
            cursor.close()
            
            return float(resultado[0]) if resultado else 0.0
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar total de custo: {e}")
            cursor.close()
            return 0.0
    
    def get_custo_total_periodo(self, data_inicio: str, data_fim: str) -> float:
        """
        Calcula o custo total em um período
        
        Args:
            data_inicio (str): Data de início
            data_fim (str): Data de fim
        
        Returns:
            float: Custo total no período
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT SUM(valor_total) as total
                FROM {} 
                WHERE data_calculo >= %s 
                AND data_calculo <= %s
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (data_inicio, data_fim))
            resultado = cursor.fetchone()
            cursor.close()
            
            total = resultado[0] if resultado[0] is not None else 0.0
            return float(total)
            
        except psycopg2.Error as e:
            print(f"Erro ao calcular custo total do período: {e}")
            cursor.close()
            return 0.0
    
    def get_custo_medio_diario(self, dias: int = 30) -> float:
        """
        Calcula o custo médio diário dos últimos N dias
        
        Args:
            dias (int): Número de dias para calcular a média
        
        Returns:
            float: Custo médio diário
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT AVG(valor_total) as media
                FROM {} 
                WHERE data_calculo >= NOW() - INTERVAL '%s days'
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (dias,))
            resultado = cursor.fetchone()
            cursor.close()
            
            media = resultado[0] if resultado[0] is not None else 0.0
            return float(media)
            
        except psycopg2.Error as e:
            print(f"Erro ao calcular custo médio diário: {e}")
            cursor.close()
            return 0.0
    
    def find_com_detalhes(self, id_custo: int) -> Optional[Dict[str, Any]]:
        """
        Busca um custo com detalhes do consumo e tarifa
        
        Args:
            id_custo (int): ID do custo
        
        Returns:
            dict: Dados do custo com detalhes
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT 
                    c.id_custo,
                    c.data_calculo,
                    c.valor_total,
                    co.id_consumo,
                    co.consumo_kwh,
                    co.data_inicio as consumo_inicio,
                    co.data_fim as consumo_fim,
                    t.id_tarifa,
                    t.valor_tarifa,
                    t.data_inicio_vigencia,
                    t.data_fim_vigencia
                FROM {} c
                JOIN CONSUMO co ON c.id_consumo = co.id_consumo
                JOIN TARIFA t ON c.id_tarifa = t.id_tarifa
                WHERE c.id_custo = %s
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_custo,))
            resultado = cursor.fetchone()
            cursor.close()
            
            if resultado:
                return {
                    'id_custo': resultado[0],
                    'data_calculo': resultado[1],
                    'valor_total': resultado[2],
                    'consumo': {
                        'id_consumo': resultado[3],
                        'consumo_kwh': resultado[4],
                        'data_inicio': resultado[5],
                        'data_fim': resultado[6]
                    },
                    'tarifa': {
                        'id_tarifa': resultado[7],
                        'valor_tarifa': resultado[8],
                        'data_inicio_vigencia': resultado[9],
                        'data_fim_vigencia': resultado[10]
                    }
                }
            return None
            
        except psycopg2.Error as e:
            print(f"Erro ao buscar custo com detalhes: {e}")
            cursor.close()
            return None
    
    def get_resumo_custos(self, id_consumo: int) -> Dict[str, Any]:
        """
        Obtém um resumo dos custos de um consumo
        
        Args:
            id_consumo (int): ID do consumo
        
        Returns:
            dict: Resumo com total, médias, etc.
        """
        cursor = self.db.cursor()
        try:
            query = sql.SQL("""
                SELECT 
                    COUNT(*) as total_registros,
                    SUM(valor_total) as soma_total,
                    AVG(valor_total) as media,
                    MIN(valor_total) as minimo,
                    MAX(valor_total) as maximo
                FROM {} 
                WHERE id_consumo = %s
            """).format(sql.Identifier(self.table))
            
            cursor.execute(query, (id_consumo,))
            resultado = cursor.fetchone()
            cursor.close()
            
            if resultado:
                return {
                    'total_registros': resultado[0],
                    'soma_total': float(resultado[1]) if resultado[1] else 0.0,
                    'media': float(resultado[2]) if resultado[2] else 0.0,
                    'minimo': float(resultado[3]) if resultado[3] else 0.0,
                    'maximo': float(resultado[4]) if resultado[4] else 0.0
                }
            return {
                'total_registros': 0,
                'soma_total': 0.0,
                'media': 0.0,
                'minimo': 0.0,
                'maximo': 0.0
            }
            
        except psycopg2.Error as e:
            print(f"Erro ao gerar resumo de custos: {e}")
            cursor.close()
            return {
                'total_registros': 0,
                'soma_total': 0.0,
                'media': 0.0,
                'minimo': 0.0,
                'maximo': 0.0
            }


# ============================================================
# EXEMPLO DE USO
# ============================================================
if __name__ == "__main__":
    try:
        # Instancia o modelo
        custo_model = Custo()
        print("✅ Modelo Custo inicializado com sucesso!")
        
        # Exemplo 1: Calcular um custo
        novo_id = custo_model.calcular_custo(
            id_consumo=1,
            id_tarifa=1,
            valor_total=150.75
        )
        print(f" Custo criado com ID: {novo_id}")
        
        # Exemplo 2: Buscar custo por consumo
        custo = custo_model.find_by_consumo(1)
        if custo:
            print(f"\n Custo do consumo 1:")
            print(f"  - ID: {custo['id_custo']}")
            print(f"  - Valor: R$ {custo['valor_total']:.2f}")
            print(f"  - Data: {custo['data_calculo']}")
        
        # Exemplo 3: Buscar custos por tarifa
        custos = custo_model.find_by_tarifa(1)
        print(f"\n  Custos com tarifa 1: {len(custos)} registros")
        
        # Exemplo 4: Resumo de custos
        resumo = custo_model.get_resumo_custos(1)
        print(f"\n Resumo de custos do consumo 1:")
        print(f"  - Total de registros: {resumo['total_registros']}")
        print(f"  - Soma total: R$ {resumo['soma_total']:.2f}")
        print(f"  - Média: R$ {resumo['media']:.2f}")
        print(f"  - Mínimo: R$ {resumo['minimo']:.2f}")
        print(f"  - Máximo: R$ {resumo['maximo']:.2f}")
        
        # Exemplo 5: Custo total do período
        total_periodo = custo_model.get_custo_total_periodo(
            '2026-01-01 00:00:00',
            '2026-12-31 23:59:59'
        )
        print(f"\n Custo total em 2026: R$ {total_periodo:.2f}")
        
    except Exception as e:
        print(f" Erro: {e}")