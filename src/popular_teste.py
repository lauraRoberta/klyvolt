"""
Script de teste: cria um registro de teste em cada tabela da cadeia
empresa -> usuario -> setor -> maquina -> sensor, para permitir testar
o simulador de sensores.

Coloque este arquivo em: backend/src/popular_teste.py
Rode com: python -m src.popular_teste
"""

from src.database.conexao import conectar


def popular():
    conn = conectar()
    cur = conn.cursor()

    try:
        # 1. Empresa
        cur.execute("""
            INSERT INTO empresa (cnpj, nome_empresa, email_empresa, senha_empresa, telefone_empresa)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_empresa
        """, ('00.000.000/0001-00', 'Faccao Teste', 'teste@faccaoteste.com', 'senha_teste', '11999999999'))
        id_empresa = cur.fetchone()[0]
        print(f"Empresa criada: id_empresa={id_empresa}")

        # 2. Usuario
        cur.execute("""
            INSERT INTO usuario (nome_usuario, email_usuario, senha_usuario, tipo_usuario, id_empresa)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_usuario
        """, ('Usuario Teste', 'usuario@teste.com', 'senha_teste', 'Administrador', id_empresa))
        id_usuario = cur.fetchone()[0]
        print(f"Usuario criado: id_usuario={id_usuario}")

        # 3. Setor
        cur.execute("""
            INSERT INTO setor (nome_setor, divisao_setor, id_usuario_responsavel)
            VALUES (%s, %s, %s)
            RETURNING id_setor
        """, ('Costura', 'Producao', id_usuario))
        id_setor = cur.fetchone()[0]
        print(f"Setor criado: id_setor={id_setor}")

        # 4. Maquina
        cur.execute("""
            INSERT INTO maquina (nome_maquina, descricao_maquina, potencia_nominal, numero_serie, id_setor)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id_maquina
        """, ('Maquina de Costura 01', 'Maquina reta industrial', 500, 'SN-0001', id_setor))
        id_maquina = cur.fetchone()[0]
        print(f"Maquina criada: id_maquina={id_maquina}")

        # 5. Sensor
        # ATENÇÃO: confira em simulador_sensores.py qual valor de 'status'
        # ele espera para considerar o sensor ativo (ex: 'ativo', 'ATIVO'...)
        cur.execute("""
            INSERT INTO sensor (
                numero_serie, fabricante, modelo, tipo_sensor, unidade_medida,
                protocolo_comunicacao, mac_address, status_conexao, status, id_maquina
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_sensor
        """, (
            'SENSOR-0001', 'Fabricante Teste', 'Modelo X', 'energia', 'kWh',
            'MQTT', 'AA:BB:CC:DD:EE:01', 'online', 'ativo', id_maquina
        ))
        id_sensor = cur.fetchone()[0]
        print(f"Sensor criado: id_sensor={id_sensor}")

        conn.commit()
        print("\nCadeia de teste criada com sucesso!")

    except Exception as e:
        conn.rollback()
        print(f"Erro ao popular dados de teste: {e}")
        raise

    finally:
        cur.close()
        conn.close()
        print("Conexao fechada.")


if __name__ == "__main__":
    popular()
