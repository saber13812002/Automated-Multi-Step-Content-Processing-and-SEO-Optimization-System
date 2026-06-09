#!/usr/bin/env bash
# Run full pytest suite for ai_benchmarker.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

if [[ -x "${ROOT}/.venv/bin/pytest" ]]; then
  PYTEST="${ROOT}/.venv/bin/pytest"
elif command -v pytest >/dev/null 2>&1; then
  PYTEST="pytest"
else
  echo "ERROR: pytest not found. Run: bash scripts/install-offline.sh"
  exit 1
fi

TEST_DB="${TMPDIR:-/tmp}/ai_benchmarker_test.db"
export DATABASE_URL="${DATABASE_URL:-sqlite:///${TEST_DB}}"
export PYTHONPATH="${ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

# Refresh editable install when wheels are available (offline-safe).
if [[ -d "${ROOT}/wheels" ]] && ls "${ROOT}"/wheels/*.whl >/dev/null 2>&1; then
  if [[ -x "${ROOT}/.venv/bin/pip" ]]; then
    PIP_NO_BUILD_ISOLATION=1 "${ROOT}/.venv/bin/pip" install \
      --no-index --find-links "${ROOT}/wheels" \
      --no-build-isolation -e "${ROOT}" -q 2>/dev/null || true
  fi
fi

echo "==> Running tests in ${ROOT}"
"${PYTEST}" tests -v --tb=short "$@"
