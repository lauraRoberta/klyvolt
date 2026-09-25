"""
Script de teste: cadastra uma máquina nova (Costura Industrial) e um
sensor novo vinculado a ela, gera uma leitura com valor ALTO de consumo
(simulando um pico de energia), garante que existe uma decisao de
"alto consumo" cadastrada, e registra a tomada_decisao vinculando a
leitura a essa decisao, com o aviso "Alto consumo de energia identificado".

Coloque este arquivo em: backend/src/popular_alerta.py
Rode com: python -m src.popular_alerta
"""

import random
from datetime import datetime

from src.database.conexao import conectar

NOME_SETOR_ALVO = 'Costura'  # busca pelo nome, nao pelo id (evita quebrar se o id mudar)
LIMITE_KWH = 20.0  # a partir daqui e considerado "alto consumo"


def popular():
    conn = conectar()
    cur = conn.cursor()

    # Sufixo aleatorio para nao colidir com dados de execucoes anteriores
    sufixo = random.randint(1000, 9999)

    try:
        # 0. Busca o id do setor pelo nome (mais robusto que um id fixo)
        cur.execute("SELECT id_setor FROM setor WHERE nome_setor LIKE %s LIMIT 1", (f'{NOME_SETOR_ALVO}%',))
        row = cur.fetchone()
        if not row:
            raise Exception(f"Nenhum setor encontrado com nome parecido com '{NOME_SETOR_ALVO}'. Rode o popular_teste.py primeiro.")
        id_setor_alvo = row[0]
        print(f"Setor encontrado: id_setor={id_setor_alvo}")

        # 1. Cadastra a máquina nova (separada da Galoneira)
        cur.execute("""
            INSERT INTO maquina (nome_maquina, descricao_maquina, potencia_nominal, numero_serie, id_setor)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_maquina
        """, (f'Maquina de Costura Industrial {sufixo}', 'Maquina de costura reta industrial',
              750, f'COST-IND-{sufixo}', id_setor_alvo))
        id_maquina = cur.fetchone()[0]
        print(f"Maquina criada: id_maquina={id_maquina}")

        # 2. Cadastra o sensor novo, vinculado a essa máquina nova
        cur.execute("""
            INSERT INTO sensor (
                numero_serie, fabricante, modelo, tipo_sensor, unidade_medida,
                protocolo_comunicacao, mac_address, status_conexao, status, id_maquina
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_sensor
        """, (
            f'SENSOR-{sufixo}', 'Fabricante Teste', 'Modelo Pico', 'energia', 'kWh',
            'MQTT', f'AA:BB:CC:DD:{sufixo // 100:02X}:{sufixo % 100:02X}', 'online', 'ativo', id_maquina
        ))
        id_sensor = cur.fetchone()[0]
        print(f"Sensor de pico criado: id_sensor={id_sensor}")

        # 3. Gera um valor ALTO de leitura (simulando pico de energia)
        valor_medido = round(random.uniform(LIMITE_KWH + 1, LIMITE_KWH + 15), 2)
        cur.execute("""
            INSERT INTO leitura (data_leitura, valor_medido_kwh, observacao_leitura, id_sensor)
            VALUES (%s, %s, %s, %s)
            RETURNING id_leitura
        """, (datetime.now(), valor_medido, 'Leitura simulada com pico de energia', id_sensor))
        id_leitura = cur.fetchone()[0]
        print(f"Leitura criada: id_leitura={id_leitura}, valor_medido_kwh={valor_medido}")

        # 4. Garante que existe uma decisao de "alto consumo" cadastrada
        cur.execute("""
            SELECT id_decisao FROM decisao WHERE nome_decisao = %s
        """, ('Alto consumo de energia',))
        row = cur.fetchone()

        if row:
            id_decisao = row[0]
            print(f"Decisao ja existia: id_decisao={id_decisao}")
        else:
            cur.execute("""
                INSERT INTO decisao (
                    nome_decisao, descricao_decisao, criterio_acionado,
                    operador, limite_referencia, unidade_limite
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id_decisao
            """, (
                'Alto consumo de energia',
                'Disparado quando uma leitura ultrapassa o limite de consumo esperado',
                'valor_medido_kwh', '>', LIMITE_KWH, 'kWh'
            ))
            id_decisao = cur.fetchone()[0]
            print(f"Decisao criada: id_decisao={id_decisao}")

        # 5. Registra a tomada de decisao (o alerta em si)
        cur.execute("""
            INSERT INTO tomada_decisao (
                data_tomada_decisao, valor_referencia, status_execucao,
                observacao, id_decisao, id_leitura
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id_tomada_decisao
        """, (
            datetime.now(), valor_medido, 'executada',
            'Alto consumo de energia identificado', id_decisao, id_leitura
        ))
        id_tomada_decisao = cur.fetchone()[0]
        print(f"Tomada de decisao criada: id_tomada_decisao={id_tomada_decisao}")

        conn.commit()
        print("\nAlerta de pico de energia registrado com sucesso!")
        print(f"-> Alto consumo de energia identificado ({valor_medido} kWh)")

    except Exception as e:
        conn.rollback()
        print(f"Erro ao registrar alerta: {e}")
        raise

    finally:
        cur.close()
        conn.close()
        print("Conexao fechada.")


if __name__ == "__main__":
    popular()