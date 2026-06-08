#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
docker build -t whisper-base:latest -f "$SCRIPT_DIR/Dockerfile" "$SCRIPT_DIR"
echo "Built whisper-base:latest"
