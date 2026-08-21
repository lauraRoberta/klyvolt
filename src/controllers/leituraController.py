
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import psycopg2
from psycopg2 import sql
from datetime import datetime
import sys
import os

# Adiciona o diretório src ao path para importar os módulos
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# ============================================================
# AUTOLOAD SIMULADO (equivalente ao spl_autoload_register)
# ============================================================
def autoload(class_name):
    """Simula o autoload do PHP"""
    if class_name.startswith('GestaoEnergia\\'):
        relative_path = class_name.replace('GestaoEnergia\\', '').replace('\\', '/')
        file_path = os.path.join(os.path.dirname(__file__), '..', 'src', relative_path + '.py')
        if os.path.exists(file_path):
            import importlib.util
            spec = importlib.util.spec_from_file_location(class_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    return None

# Tentar importar o controlador
try:
    from GestaoEnergia.Controllers.LeituraController import LeituraController
except ImportError:
    # Se não encontrar, cria um controller mock para demonstração
    class LeituraController:
        def registrar(self, dados):
            print(f"DEBUG: Registrando leitura - Máquina: {dados['id_maquina']}, Valor: {dados['valor_kwh']}")
            return {'success': True, 'message': 'Leitura registrada com sucesso!'}

# ============================================================
# CONEXÃO POSTGRESQL
# ============================================================
try:
    conn = psycopg2.connect(
        host='localhost',
        port='5432',
        database='gestao_energetica',
        user='postgres',
        password=''
    )
    conn.autocommit = False
    cursor = conn.cursor()
    print("✅ Conectado ao PostgreSQL com sucesso!")
    print()
except psycopg2.Error as e:
    print(f"❌ Erro ao conectar: {e}")
    sys.exit(1)

# ============================================================
# FUNÇÕES AUXILIARES PARA EXIBIÇÃO
# ============================================================
def print_table(headers, rows):
    """Exibe uma tabela formatada no terminal"""
    if not rows:
        return
    
    # Calcular largura das colunas
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell) if cell is not None else ''))
    
    # Criar linha separadora
    separator = '+' + '+'.join(['-' * (w + 2) for w in col_widths]) + '+'
    
    # Imprimir cabeçalho
    print(separator)
    header_row = '| ' + ' | '.join([str(h).ljust(col_widths[i]) for i, h in enumerate(headers)]) + ' |'
    print(header_row)
    print(separator)
    
    # Imprimir dados
    for row in rows:
        data_row = '| ' + ' | '.join([str(cell if cell is not None else '').ljust(col_widths[i]) for i, cell in enumerate(row)]) + ' |'
        print(data_row)
    print(separator)

# ============================================================
# LISTAR EMPRESAS
# ============================================================
print("🏢 Empresas")
print("-" * 40)
try:
    cursor.execute("SELECT id_empresa, nome_empresa, email_empresa FROM EMPRESA")
    empresas = cursor.fetchall()
    
    if empresas:
        print_table(['ID', 'Nome', 'Email'], empresas)
    else:
        print("Nenhuma empresa cadastrada.")
except psycopg2.Error as e:
    print(f"Erro ao listar empresas: {e}")
print()

# ============================================================
# LISTAR MÁQUINAS
# ============================================================
print("⚙️ Máquinas")
print("-" * 40)
try:
    cursor.execute("SELECT id_maquina, nome_maquina, descricao_maquina FROM MAQUINA")
    maquinas = cursor.fetchall()
    
    if maquinas:
        print_table(['ID', 'Nome', 'Descrição'], maquinas)
    else:
        print("Nenhuma máquina cadastrada.")
except psycopg2.Error as e:
    print(f"Erro ao listar máquinas: {e}")
print()

# ============================================================
# FORMULÁRIO PARA REGISTRAR LEITURA
# ============================================================
print("📊 Nova Leitura")
print("-" * 40)

# Obter lista de máquinas para o select
try:
    cursor.execute("SELECT id_maquina, nome_maquina FROM MAQUINA")
    maquinas_list = cursor.fetchall()
    
    if not maquinas_list:
        print("Nenhuma máquina disponível para registrar leitura.")
    else:
        # Exibir máquinas disponíveis
        print("Máquinas disponíveis:")
        for i, (id_maq, nome_maq) in enumerate(maquinas_list, 1):
            print(f"  {i}. {nome_maq} (ID: {id_maq})")
        
        # Solicitar dados ao usuário
        while True:
            try:
                escolha = int(input("\nDigite o número da máquina: "))
                if 1 <= escolha <= len(maquinas_list):
                    id_maquina = maquinas_list[escolha - 1][0]
                    break
                else:
                    print("Opção inválida. Tente novamente.")
            except ValueError:
                print("Digite um número válido.")
        
        valor_kwh = input("Valor (kWh): ")
        try:
            valor_kwh = float(valor_kwh)
        except ValueError:
            print("Valor inválido. Usando 0.0")
            valor_kwh = 0.0
        
        observacao = input("Observação (opcional): ") or None
        
        # Confirmar registro
        print(f"\nConfirmar registro?")
        print(f"  Máquina: {maquinas_list[escolha-1][1]}")
        print(f"  Valor: {valor_kwh} kWh")
        print(f"  Observação: {observacao or '(vazio)'}")
        
        confirmar = input("Registrar? (s/N): ").lower()
        
        if confirmar == 's':
            # ============================================================
            # PROCESSAR FORMULÁRIO
            # ============================================================
            controller = LeituraController()
            resultado = controller.registrar({
                'id_maquina': id_maquina,
                'valor_kwh': valor_kwh,
                'observacao': observacao,
                'id_usuario': 1
            })
            
            if resultado.get('success', False):
                print(f"\n✅ {resultado.get('message', 'Leitura registrada com sucesso!')}")
            else:
                print(f"\n❌ {resultado.get('message', 'Erro ao registrar leitura')}")
        else:
            print("\nRegistro cancelado.")
            
except psycopg2.Error as e:
    print(f"Erro ao listar máquinas: {e}")
print()

# ============================================================
# LISTAR ÚLTIMAS LEITURAS
# ============================================================
print("📋 Últimas Leituras")
print("-" * 40)
try:
    cursor.execute("""
        SELECT l.data_leitura, l.valor_medido_kwh, m.nome_maquina 
        FROM LEITURA l 
        JOIN MAQUINA m ON l.id_maquina = m.id_maquina 
        ORDER BY l.data_leitura DESC 
        LIMIT 10
    """)
    leituras = cursor.fetchall()
    
    if leituras:
        print_table(['Data', 'Valor (kWh)', 'Máquina'], leituras)
    else:
        print("Nenhuma leitura registrada.")
except psycopg2.Error as e:
    print(f"Erro ao listar leituras: {e}")

# ============================================================
# FECHAR CONEXÃO
# ============================================================
cursor.close()
conn.close()
print("\n✅ Conexão fechada.")