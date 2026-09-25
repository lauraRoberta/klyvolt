"""
Simulação completa de um sensor, ponta a ponta, passando por TODAS as
tabelas do sistema Klyvolt:

    empresa -> usuario -> setor -> maquina -> sensor
        -> leitura -> consumo
        -> decisao -> tomada_decisao (somente se o consumo ultrapassar o limite)

Cada execução cria uma cadeia nova e independente (nova empresa, novo
setor, nova máquina, novo sensor), então rodar várias vezes gera vários
cenários de teste sem conflitar uns com os outros.

Coloque este arquivo em: backend/src/simulacao_completa.py
Rode com: python -m src.simulacao_completa
"""

import random
from datetime import datetime, timedelta

from src.database.conexao import conectar

# Nome da decisão usada para avaliar alto consumo (reaproveitada se já existir)
NOME_DECISAO = 'Alto consumo de energia'
LIMITE_KWH = 20.0


def buscar_ou_criar_decisao(cur):
    """Garante que existe uma decisao de alto consumo cadastrada e retorna seu id."""
    cur.execute("SELECT id_decisao FROM decisao WHERE nome_decisao = %s", (NOME_DECISAO,))
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute("""
        INSERT INTO decisao (
            nome_decisao, descricao_decisao, criterio_acionado,
            operador, limite_referencia, unidade_limite
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id_decisao
    """, (
        NOME_DECISAO,
        'Disparado quando o consumo de uma maquina ultrapassa o limite esperado',
        'consumo_kwh', '>', LIMITE_KWH, 'kWh'
    ))
    return cur.fetchone()[0]


def simular():
    conn = conectar()
    cur = conn.cursor()

    # Sufixo aleatorio para nao colidir com numero_serie/mac/cnpj/email ja usados
    sufixo = random.randint(1000, 9999)

    try:
        # 1. Empresa
        cur.execute("""
            INSERT INTO empresa (cnpj, nome_empresa, email_empresa, senha_empresa, telefone_empresa)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_empresa
        """, (f'00.000.000/{sufixo:04d}-00', f'Faccao Simulada {sufixo}',
              f'contato{sufixo}@faccaosimulada.com', 'senha_teste', '11999999999'))
        id_empresa = cur.fetchone()[0]
        print(f"[1/9] Empresa criada: id_empresa={id_empresa}")

        # 2. Usuario
        cur.execute("""
            INSERT INTO usuario (nome_usuario, email_usuario, senha_usuario, tipo_usuario, id_empresa)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_usuario
        """, (f'Usuario Simulado {sufixo}', f'usuario{sufixo}@teste.com', 'senha_teste',
              'Administrador', id_empresa))
        id_usuario = cur.fetchone()[0]
        print(f"[2/9] Usuario criado: id_usuario={id_usuario}")

        # 3. Setor
        cur.execute("""
            INSERT INTO setor (nome_setor, divisao_setor, id_usuario_responsavel)
            VALUES (%s, %s, %s)
            RETURNING id_setor
        """, (f'Setor Simulado {sufixo}', 'Producao', id_usuario))
        id_setor = cur.fetchone()[0]
        print(f"[3/9] Setor criado: id_setor={id_setor}")

        # 4. Maquina
        cur.execute("""
            INSERT INTO maquina (nome_maquina, descricao_maquina, potencia_nominal, numero_serie, id_setor)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_maquina
        """, (f'Maquina Simulada {sufixo}', 'Maquina de teste gerada por simulacao',
              500, f'SIM-{sufixo}', id_setor))
        id_maquina = cur.fetchone()[0]
        print(f"[4/9] Maquina criada: id_maquina={id_maquina}")

        # 5. Sensor
        mac = f'AA:BB:CC:DD:{sufixo // 100:02X}:{sufixo % 100:02X}'
        cur.execute("""
            INSERT INTO sensor (
                numero_serie, fabricante, modelo, tipo_sensor, unidade_medida,
                protocolo_comunicacao, mac_address, status_conexao, status, id_maquina
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_sensor
        """, (f'SENSOR-SIM-{sufixo}', 'Fabricante Simulado', 'Modelo Sim',
              'energia', 'kWh', 'MQTT', mac, 'online', 'ativo', id_maquina))
        id_sensor = cur.fetchone()[0]
        print(f"[5/9] Sensor criado: id_sensor={id_sensor}")

        # 6. Leitura (valor aleatorio, podendo ou nao ultrapassar o limite)
        valor_medido = round(random.uniform(5, 35), 2)
        data_leitura = datetime.now()
        cur.execute("""
            INSERT INTO leitura (data_leitura, valor_medido_kwh, observacao_leitura, id_sensor, id_usuario)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_leitura
        """, (data_leitura, valor_medido, 'Leitura gerada por simulacao completa', id_sensor, id_usuario))
        id_leitura = cur.fetchone()[0]
        print(f"[6/9] Leitura criada: id_leitura={id_leitura}, valor_medido_kwh={valor_medido}")

        # 7. Consumo (janela de 1 hora terminando na leitura)
        data_inicio = data_leitura - timedelta(hours=1)
        data_fim = data_leitura
        cur.execute("""
            INSERT INTO consumo (data_inicio, data_fim, consumo_kwh, id_maquina)
            VALUES (%s, %s, %s, %s)
            RETURNING id_consumo
        """, (data_inicio, data_fim, valor_medido, id_maquina))
        id_consumo = cur.fetchone()[0]
        print(f"[7/9] Consumo criado: id_consumo={id_consumo}, consumo_kwh={valor_medido}")

        # 8. Decisao (catalogo de regras, reaproveitado se ja existir)
        id_decisao = buscar_ou_criar_decisao(cur)
        print(f"[8/9] Decisao pronta: id_decisao={id_decisao} (limite: {LIMITE_KWH} kWh)")

        # 9. Tomada de decisao (so dispara se ultrapassar o limite)
        if valor_medido > LIMITE_KWH:
            cur.execute("""
                INSERT INTO tomada_decisao (
                    data_tomada_decisao, valor_referencia, status_execucao,
                    observacao, id_decisao, id_leitura, id_consumo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id_tomada_decisao
            """, (datetime.now(), valor_medido, 'executada',
                  'Alto consumo de energia identificado', id_decisao, id_leitura, id_consumo))
            id_tomada_decisao = cur.fetchone()[0]
            print(f"[9/9] Tomada de decisao criada: id_tomada_decisao={id_tomada_decisao} -> ALERTA disparado!")
        else:
            print(f"[9/9] Consumo dentro do limite ({valor_medido} kWh <= {LIMITE_KWH} kWh) - nenhum alerta disparado")

        conn.commit()
        print("\nSimulacao completa registrada com sucesso em todas as tabelas!")

    except Exception as e:
        conn.rollback()
        print(f"Erro na simulacao: {e}")
        raise

    finally:
        cur.close()
        conn.close()
        print("Conexao fechada.")


if __name__ == "__main__":
    simular()
