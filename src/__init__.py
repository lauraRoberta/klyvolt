# -*- coding: utf-8 -*-
# Arquivo: src/__init__.py

"""
Pacote principal do sistema de gestão energética
"""

__version__ = '1.0.0'
__author__ = 'Seu Nome'
__description__ = 'Sistema de gestão de energia elétrica'

# Importações principais para facilitar o uso
from GestaoEnergia.Database.Connection import Connection
from GestaoEnergia.Controllers.LeituraController import LeituraController
from GestaoEnergia.Models.Leitura import Leitura
from GestaoEnergia.Models.Consumo import Consumo
from GestaoEnergia.Models.Custo import Custo
from GestaoEnergia.Models.Empresa import Empresa
from GestaoEnergia.Models.Maquina import Maquina

__all__ = [
    'Connection',
    'LeituraController',
    'Leitura',
    'Consumo',
    'Custo',
    'Empresa',
    'Maquina',
]