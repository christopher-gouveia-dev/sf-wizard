#!/usr/bin/env bash
set -euo pipefail

# Simple dev helper (no Docker).
# - Starts API on :8000
# - Starts Web on :5173

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Starting API..."
( cd "${ROOT_DIR}/apps/api" &&   python -m venv .venv >/dev/null 2>&1 || true &&   source .venv/bin/activate &&   pip install -r requirements.txt &&   uvicorn sf_wizard.main:app --reload --host 127.0.0.1 --port 8000 ) &

API_PID=$!

echo "Starting Web..."
( cd "${ROOT_DIR}/apps/web" && npm install && npm run dev ) &

WEB_PID=$!

trap 'kill ${API_PID} ${WEB_PID} 2>/dev/null || true' EXIT
wait
