#!/usr/bin/env bash
# Build Docker image fully offline (wheels/ must exist; base image must be cached locally).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-ai-benchmark:latest}"
TAR_OUTPUT="${TAR_OUTPUT:-${ROOT}/ai-benchmark.tar}"
WHEELS_DIR="${ROOT}/wheels"

cd "${ROOT}"

if [[ ! -d "${WHEELS_DIR}" ]] || [[ -z "$(find "${WHEELS_DIR}" -maxdepth 1 -name '*.whl' 2>/dev/null)" ]]; then
  echo "ERROR: No wheels found in ${WHEELS_DIR}"
  echo "On a machine with internet, run:"
  echo "  bash scripts/download-wheels.sh"
  echo "  # or on Windows: powershell -File scripts/download-wheels.ps1"
  exit 1
fi

if ! docker image inspect python:3.12-slim >/dev/null 2>&1; then
  echo "ERROR: Base image python:3.12-slim is not available locally."
  echo "On a machine with internet, run once:"
  echo "  docker pull python:3.12-slim"
  echo "  docker save -o python-3.12-slim.tar python:3.12-slim"
  echo "On this offline server:"
  echo "  docker load -i python-3.12-slim.tar"
  exit 1
fi

echo "==> Building ${IMAGE_NAME} (offline, no network)..."
DOCKER_BUILDKIT=1 docker build \
  --network=none \
  -t "${IMAGE_NAME}" \
  .

echo "==> Saving image to ${TAR_OUTPUT}..."
docker save -o "${TAR_OUTPUT}" "${IMAGE_NAME}"

echo ""
echo "Build complete."
echo "  Image : ${IMAGE_NAME}"
echo "  Tar   : ${TAR_OUTPUT}"
echo ""
echo "Transfer to offline server:"
echo "  scp ${TAR_OUTPUT} user@server:/path/"
echo ""
echo "On offline server:"
echo "  docker load -i ai-benchmark.tar"
echo "  docker run -d -p 8000:8000 -v ai_benchmarker_data:/data --name ai-benchmarker ${IMAGE_NAME}"
