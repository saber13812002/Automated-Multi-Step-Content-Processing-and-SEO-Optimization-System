#!/usr/bin/env bash
# Run on a machine WITH internet (Linux/macOS/Git Bash on Windows).
# Downloads all wheels into wheels/ for offline pip install and Docker build.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WHEELS_DIR="${ROOT}/wheels"
PYTHON="${PYTHON:-python3}"

mkdir -p "${WHEELS_DIR}"

echo "==> Downloading build tools..."
"${PYTHON}" -m pip download \
  -r "${ROOT}/requirements.build.txt" \
  -d "${WHEELS_DIR}"

echo "==> Downloading runtime dependencies..."
"${PYTHON}" -m pip download \
  -r "${ROOT}/requirements.docker.txt" \
  -d "${WHEELS_DIR}"

echo "==> Downloading dev/test dependencies..."
"${PYTHON}" -m pip download \
  -r "${ROOT}/requirements.txt" \
  -d "${WHEELS_DIR}"

echo "==> Building project wheel..."
"${PYTHON}" -m pip wheel \
  "${ROOT}" \
  --no-deps \
  -w "${WHEELS_DIR}"

COUNT="$(find "${WHEELS_DIR}" -maxdepth 1 -name '*.whl' | wc -l | tr -d ' ')"
echo ""
echo "Done. ${COUNT} wheel file(s) in: ${WHEELS_DIR}"
echo ""
echo "Next steps:"
echo "  1. git add wheels/ && git commit && git push"
echo "  2. On offline server: bash scripts/build-offline-docker.sh"
echo "     OR transfer ai-benchmark.tar after docker save on this machine"
