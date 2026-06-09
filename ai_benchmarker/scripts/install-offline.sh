#!/usr/bin/env bash
# Install ai_benchmarker without internet using wheels/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WHEELS_DIR="${ROOT}/wheels"
VENV="${ROOT}/.venv"

if [[ ! -d "${WHEELS_DIR}" ]] || [[ -z "$(ls -A "${WHEELS_DIR}"/*.whl 2>/dev/null)" ]]; then
  echo "ERROR: ${WHEELS_DIR} is empty or missing."
  echo "On Windows (with internet, NO Docker needed), run:"
  echo "  powershell -ExecutionPolicy Bypass -File scripts/download-wheels-linux.ps1"
  echo "  git add wheels/ && git commit -m 'Linux wheels' && git push"
  exit 1
fi

if [[ ! -d "${VENV}" ]]; then
  python3 -m venv "${VENV}"
fi

"${VENV}/bin/pip" install --upgrade pip setuptools wheel \
  --no-index \
  --find-links "${WHEELS_DIR}"

PIP_NO_BUILD_ISOLATION=1 "${VENV}/bin/pip" install \
  --no-index \
  --find-links "${WHEELS_DIR}" \
  --no-build-isolation \
  -r "${ROOT}/requirements.txt" \
  "${ROOT}"

echo ""
echo "Install complete. Activate and run:"
echo "  source .venv/bin/activate"
echo "  uvicorn ai_benchmarker.app:app --host 0.0.0.0 --port 8090 --reload"
