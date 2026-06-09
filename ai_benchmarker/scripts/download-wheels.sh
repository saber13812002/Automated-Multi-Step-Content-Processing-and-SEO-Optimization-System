#!/usr/bin/env bash
# Run this script on a machine WITH internet access.
# It downloads all runtime + dev wheels into vendor/wheels/ for offline install.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WHEELS_DIR="${ROOT}/vendor/wheels"

mkdir -p "${WHEELS_DIR}"

python3 -m pip download \
  -r "${ROOT}/requirements.txt" \
  -d "${WHEELS_DIR}"

python3 -m pip download \
  "${ROOT}" \
  -d "${WHEELS_DIR}"

echo "Wheels saved to: ${WHEELS_DIR}"
echo "Copy the vendor/ folder to the offline server, then run:"
echo "  bash scripts/install-offline.sh"
