#!/usr/bin/env bash
# Standard online install. If this fails with "Network is unreachable",
# use scripts/download-wheels.sh on another machine + scripts/install-offline.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${ROOT}/.venv"

if [[ ! -d "${VENV}" ]]; then
  python3 -m venv "${VENV}"
fi

# Prefer IPv4 when the host has broken IPv6 routing.
export PIP_DEFAULT_TIMEOUT="${PIP_DEFAULT_TIMEOUT:-120}"

"${VENV}/bin/pip" install --upgrade pip setuptools wheel

# --no-build-isolation avoids a second pip round-trip for build deps.
PIP_NO_BUILD_ISOLATION=1 "${VENV}/bin/pip" install --no-build-isolation -r "${ROOT}/requirements.txt" -e "${ROOT}"

echo ""
echo "Install complete. Activate and run:"
echo "  source .venv/bin/activate"
echo "  uvicorn ai_benchmarker.app:app --host 0.0.0.0 --port 8090 --reload"
