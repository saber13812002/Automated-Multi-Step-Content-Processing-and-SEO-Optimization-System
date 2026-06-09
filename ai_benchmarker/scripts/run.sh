#!/usr/bin/env bash
# Start AI Benchmarker API (no Docker).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${ROOT}/.venv"

if [[ ! -x "${VENV}/bin/uvicorn" ]]; then
  echo "ERROR: uvicorn not found. Run: bash scripts/install-offline.sh"
  exit 1
fi

cd "${ROOT}"
source "${VENV}/bin/activate"

export APP_HOST="${APP_HOST:-0.0.0.0}"
export APP_PORT="${APP_PORT:-8090}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///${ROOT}/ai_benchmarker.db}"

exec uvicorn ai_benchmarker.app:app \
  --host "${APP_HOST}" \
  --port "${APP_PORT}"
