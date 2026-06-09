#!/usr/bin/env bash
# Download Linux (manylinux) wheels for Python 3.12 — for Docker / offline Linux server.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WHEELS_DIR="${ROOT}/wheels"
PYTHON="${PYTHON:-python3}"
PLATFORM="manylinux2014_x86_64"
PY_VERSION="3.12"

mkdir -p "${WHEELS_DIR}"

download() {
  local req="$1"
  echo "==> ${req} (linux/${PY_VERSION})"
  "${PYTHON}" -m pip download \
    -r "${ROOT}/${req}" \
    -d "${WHEELS_DIR}" \
    --platform "${PLATFORM}" \
    --python-version "${PY_VERSION}" \
    --implementation cp \
    --abi "cp312" \
    --only-binary ":all:"
}

download "requirements.build.txt"
download "requirements.docker.txt"
download "requirements.txt"

echo "==> Building project wheel..."
"${PYTHON}" -m pip wheel "${ROOT}" --no-deps -w "${WHEELS_DIR}"

COUNT="$(find "${WHEELS_DIR}" -maxdepth 1 -name '*.whl' | wc -l | tr -d ' ')"
echo ""
echo "Done. ${COUNT} wheel(s) in ${WHEELS_DIR}"
echo "Commit: git add wheels/ && git commit -m 'Linux wheels' && git push"
