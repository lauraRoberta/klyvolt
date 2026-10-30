"""Simulador de sensor do KLYVOLT (somente para testes e demonstração).

Envia leituras FICTÍCIAS pela mesma rota usada por um sensor físico
(POST /leituras/sensor com o token do sensor). Cada leitura é gravada com a
observação "LEITURA SIMULADA", para nunca ser confundida com medição real.

Uso (com a API rodando):
    python simulador_sensores.py --token tk_seu_token --quantidade 10 --intervalo 5 --confirmar

Cadastre antes um sensor de teste com status "Ativo" e um token (página Sensores).
"""
import argparse
import random
import sys
import time

import httpx

MARCA = "LEITURA SIMULADA (simulador_sensores.py)"


def main() -> int:
    parser = argparse.ArgumentParser(description="Envia leituras simuladas para um sensor de teste.")
    parser.add_argument("--token", required=True, help="Token de autenticação do sensor de teste")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="Endereço da API (padrão: %(default)s)")
    parser.add_argument("--quantidade", type=int, default=5, help="Número de leituras (padrão: %(default)s)")
    parser.add_argument("--intervalo", type=float, default=2.0, help="Segundos entre leituras (padrão: %(default)s)")
    parser.add_argument("--minimo", type=float, default=0.05, help="Menor valor em kWh (padrão: %(default)s)")
    parser.add_argument("--maximo", type=float, default=0.60, help="Maior valor em kWh (padrão: %(default)s)")
    parser.add_argument("--confirmar", action="store_true",
                        help="Obrigatório: confirma que você quer gravar dados simulados no banco")
    args = parser.parse_args()

    if not args.confirmar:
        print("Nada foi enviado. Use --confirmar para gravar leituras SIMULADAS no banco.")
        return 1
    if not 0 <= args.minimo <= args.maximo:
        print("Intervalo de valores inválido.")
        return 1

    url = args.api.rstrip("/") + "/leituras/sensor"
    for numero in range(1, args.quantidade + 1):
        valor = round(random.uniform(args.minimo, args.maximo), 2)
        try:
            resposta = httpx.post(url, headers={"X-Sensor-Token": args.token},
                                  json={"valor_medido_kwh": valor, "observacao_leitura": MARCA}, timeout=15)
        except httpx.RequestError as erro:
            print(f"Falha ao acessar a API ({type(erro).__name__}). Ela está rodando em {args.api}?")
            return 2
        if resposta.status_code != 201:
            print(f"Leitura {numero}: recusada ({resposta.status_code}) - {resposta.json().get('detail')}")
            return 3
        print(f"Leitura {numero}/{args.quantidade}: {valor:.2f} kWh gravada (id {resposta.json()['id_leitura']})")
        if numero < args.quantidade:
            time.sleep(args.intervalo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
