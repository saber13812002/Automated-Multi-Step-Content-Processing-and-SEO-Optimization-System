#!/usr/bin/env bash
# Install ai_benchmarker without internet using vendor/wheels/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WHEELS_DIR="${ROOT}/vendor/wheels"
VENV="${ROOT}/.venv"

if [[ ! -d "${WHEELS_DIR}" ]] || [[ -z "$(ls -A "${WHEELS_DIR}" 2>/dev/null)" ]]; then
  echo "ERROR: ${WHEELS_DIR} is empty or missing."
  echo "On a machine with internet, run:"
  echo "  bash scripts/download-wheels.sh"
  echo "Then copy vendor/wheels/ to this server."
  exit 1
fi

if [[ ! -d "${VENV}" ]]; then
  python3 -m venv "${VENV}"
fi

# Use existing setuptools in venv/system to avoid isolated build downloads.
"${VENV}/bin/pip" install --upgrade pip setuptools wheel \
  --no-index \
  --find-links "${WHEELS_DIR}" \
  || "${VENV}/bin/pip" install --upgrade pip setuptools wheel --no-build-isolation \
  --no-index \
  --find-links "${WHEELS_DIR}"

"${VENV}/bin/pip" install \
  --no-index \
  --find-links "${WHEELS_DIR}" \
  -e "${ROOT}[dev]"

echo ""
echo "Install complete. Activate and run:"
echo "  source .venv/bin/activate"
echo "  uvicorn ai_benchmarker.app:app --host 0.0.0.0 --port 8090 --reload"
