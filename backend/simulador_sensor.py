"""Simula o ESP32: manda leituras de vibração e temperatura para a API,
do mesmo jeito que o sensor de verdade vai mandar.

Uso (com o servidor rodando, em outro terminal):
    python simulador_sensor.py

Para parar: Ctrl + C.
Não precisa instalar nada além do Python.
"""
import json
import random
import time
import urllib.error
import urllib.request

# ===== CONFIGURE AQUI =====
URL_API = "http://localhost:8000/leituras/sensor"
ID_SENSOR = 22
TOKEN_SENSOR = "klyvolt-escola-2026-xyz789"
INTERVALO_SEGUNDOS = 10  # o ESP32 de verdade manda a cada 10 s
# ==========================

JANELAS_CALIBRACAO = 6   # igual ao código do ESP32


def enviar(corpo: dict) -> None:
    dados = json.dumps(corpo).encode("utf-8")
    pedido = urllib.request.Request(
        URL_API,
        data=dados,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Token-Sensor": TOKEN_SENSOR,
        },
    )
    try:
        with urllib.request.urlopen(pedido, timeout=5) as resposta:
            print(f"  enviado (código {resposta.status})")
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode("utf-8", errors="ignore")
        print(f"  FALHOU (código {erro.code}): {detalhe}")
    except urllib.error.URLError as erro:
        print(f"  FALHOU (sem conexão): {erro.reason}")


def main() -> None:
    print(f"Enviando para {URL_API} como sensor #{ID_SENSOR}. Ctrl + C para parar.\n")
    janela = 0
    soma = 0
    media_normal = 0.0

    while True:
        janela += 1
        vibracoes = random.randint(8, 14)

        if janela <= JANELAS_CALIBRACAO:
            estado = "calibrando"
            soma += vibracoes
            if janela == JANELAS_CALIBRACAO:
                media_normal = soma / JANELAS_CALIBRACAO
        else:
            # de vez em quando simula uma vibração fora do normal
            sorteio = random.random()
            if sorteio < 0.1:
                vibracoes = int(media_normal * 2 + 5)
                estado = "acima"
            elif sorteio < 0.15:
                vibracoes = max(0, int(media_normal * 0.2))
                estado = "abaixo"
            else:
                estado = "normal"

        corpo = {
            "id_sensor": ID_SENSOR,
            "vibracoes": vibracoes,
            "temperatura": round(random.uniform(26.0, 29.0), 1),
            "umidade": round(random.uniform(55.0, 65.0), 1),
            "estado": estado,
            "media_normal": round(media_normal, 2),
        }
        print(f"Janela {janela}: {corpo}")
        enviar(corpo)
        time.sleep(INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSimulador parado.")