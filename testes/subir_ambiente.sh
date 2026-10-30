#!/usr/bin/env bash
# Sobe o ambiente local de testes do KLYVOLT:
#   Postgres (banco recriado a partir de database/klyvolt_schema.sql)
#   Supabase local (porta 54321) → API FastAPI real (porta 8000) → frontend (porta 5500)
# Variáveis: KV_PGHOST (pasta do socket do Postgres, porta 54329) e, se necessário,
#            KV_PYTHONPATH (pacotes do backend fora do ambiente virtual).
set -e
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
LOGS="${KV_LOGS:-/tmp/klyvolt-testes}"; mkdir -p "$LOGS"
P="psql -X -q -v ON_ERROR_STOP=1 -h ${KV_PGHOST:?defina KV_PGHOST} -p 54329 -U postgres"

pkill -f "supabase_local/servidor.js" 2>/dev/null || true
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "http.server 5500" 2>/dev/null || true
sleep 0.5

$P -c "drop database if exists klyvolt" -c "create database klyvolt" >/dev/null
$P -d klyvolt -f "$RAIZ/testes/supabase_local/auth_emulacao.sql" >/dev/null
$P -d klyvolt -f "$RAIZ/database/klyvolt_schema.sql" >/dev/null
echo "✔ banco recriado a partir de database/klyvolt_schema.sql"

KV_PGHOST="$KV_PGHOST" nohup node "$RAIZ/testes/supabase_local/servidor.js" > "$LOGS/supabase.log" 2>&1 &
for i in $(seq 1 50); do curl -s http://127.0.0.1:54321/__teste/chave_anon >/dev/null 2>&1 && break; sleep 0.1; done
CHAVE=$(curl -s http://127.0.0.1:54321/__teste/chave_anon | python3 -c "import json,sys; print(json.load(sys.stdin)['chave'])")
echo "✔ Supabase local em http://127.0.0.1:54321"

cd "$RAIZ/backend"
SUPABASE_URL=http://127.0.0.1:54321 SUPABASE_KEY="$CHAVE" FRONTEND_URL=http://127.0.0.1:5500 \
  PYTHONPATH="${KV_PYTHONPATH:-}" YARL_NO_EXTENSIONS=1 MULTIDICT_NO_EXTENSIONS=1 PROPCACHE_NO_EXTENSIONS=1 \
  nohup python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 > "$LOGS/api.log" 2>&1 &
for i in $(seq 1 100); do curl -s http://127.0.0.1:8000/ >/dev/null 2>&1 && break; sleep 0.1; done
curl -sf http://127.0.0.1:8000/ >/dev/null && echo "✔ API FastAPI em http://127.0.0.1:8000 (Swagger: /docs)"

cd "$RAIZ/frontend"
nohup python3 -m http.server 5500 --bind 127.0.0.1 > "$LOGS/frontend.log" 2>&1 &
for i in $(seq 1 50); do curl -s http://127.0.0.1:5500/ >/dev/null 2>&1 && break; sleep 0.1; done
echo "✔ Frontend em http://127.0.0.1:5500"
