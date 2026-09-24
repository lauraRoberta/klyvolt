# ============================================================
# Simulador de Sensores - Klyvolt
# ------------------------------------------------------------
# Gera leituras falsas (porém realistas) para os sensores já
# cadastrados no banco, como se fossem os sensores físicos
# enviando dados. Útil para testar/demonstrar o sistema antes
# de instalar os sensores reais.
#
# As leituras geradas aqui são marcadas em "observacao_leitura"
# como "leitura simulada", para ficar fácil de identificar e
# remover depois, quando os sensores de verdade entrarem em uso:
#
#   DELETE FROM leitura WHERE observacao_leitura = 'leitura simulada';
# ============================================================

import time
import random
from datetime import datetime

import psycopg2.extras

from src.database.conexao import conectar


INTERVALO_SEGUNDOS = 5

FAIXAS_POR_TIPO = {
    "Corrente": (1.0, 8.0),
    "Tensão":   (210.0, 230.0),
    "Potência": (0.5, 4.0),
}
FAIXA_PADRAO = (1.0, 5.0)


def buscar_sensores_ativos(conexao):
    """Busca todos os sensores com status 'ativo' cadastrados no banco."""
    cursor = conexao.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(
        "SELECT id_sensor, tipo_sensor FROM sensor WHERE status = 'ativo'"
    )
    sensores = cursor.fetchall()
    cursor.close()
    return sensores


def gerar_valor_simulado(tipo_sensor):
    """Gera um valor aleatório dentro da faixa esperada para o tipo de sensor."""
    minimo, maximo = FAIXAS_POR_TIPO.get(tipo_sensor, FAIXA_PADRAO)
    return round(random.uniform(minimo, maximo), 2)


def inserir_leitura(conexao, id_sensor, valor):
    """Insere uma nova leitura simulada na tabela leitura."""
    cursor = conexao.cursor()
    sql = """
        INSERT INTO leitura (data_leitura, valor_medido_kwh, observacao_leitura, id_sensor)
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(sql, (datetime.now(), valor, "leitura simulada", id_sensor))
    conexao.commit()
    cursor.close()


def rodar_simulacao():
    conexao = conectar()
    if conexao is None:
        print("Não foi possível conectar ao banco. Encerrando.")
        return

    print("Simulador de sensores iniciado. Pressione Ctrl+C para parar.\n")

    try:
        while True:
            sensores = buscar_sensores_ativos(conexao)

            if not sensores:
                print("Nenhum sensor ativo encontrado no banco. Verifique a tabela 'sensor'.")
            else:
                for sensor in sensores:
                    valor = gerar_valor_simulado(sensor["tipo_sensor"])
                    inserir_leitura(conexao, sensor["id_sensor"], valor)
                    agora = datetime.now().strftime("%H:%M:%S")
                    print(f"[{agora}] Sensor {sensor['id_sensor']} ({sensor['tipo_sensor']}) -> {valor}")

            time.sleep(INTERVALO_SEGUNDOS)

    except KeyboardInterrupt:
        print("\nSimulação encerrada pelo usuário.")
    finally:
        conexao.close()


if __name__ == "__main__":
    rodar_simulacao()