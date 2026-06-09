#!/usr/bin/env bash
# End-to-end sample test for AI Benchmarker API.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8090}"

echo "=== AI Benchmarker E2E Test ==="
echo "Base URL: ${BASE_URL}"
echo ""

echo "1) Health check"
curl -sf "${BASE_URL}/health" | python3 -m json.tool
echo ""

REFERENCE_TEXT="سلام دنیا این یک متن مرجع برای تست بنچمارک است"
HYPOTHESIS_TEXT="سلام دنیا این یک متن مرجع برای تست بنچمارک هست"

echo "2) Create reference audio (get GUID)"
AUDIO_RESPONSE=$(curl -sf -X POST "${BASE_URL}/api/v1/audio/json" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "
import json
print(json.dumps({
    'file_name': 'sample-reference.txt',
    'approved_text': '''${REFERENCE_TEXT}''',
}))
")")
echo "${AUDIO_RESPONSE}" | python3 -m json.tool

AUDIO_GUID=$(echo "${AUDIO_RESPONSE}" | python3 -c "import sys,json; print(json.load(sys.stdin)['audio_guid'])")
REF_ID=$(echo "${AUDIO_RESPONSE}" | python3 -c "import sys,json; print(json.load(sys.stdin)['reference_transcription_id'])")
echo "GUID: ${AUDIO_GUID}"
echo "Reference transcription ID: ${REF_ID}"
echo ""

echo "3) Add Whisper transcription (slightly different text)"
WHISPER_RESPONSE=$(curl -sf -X POST "${BASE_URL}/api/v1/transcription" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "
import json
print(json.dumps({
    'audio_guid': '${AUDIO_GUID}',
    'model_name': 'whisper-large-v3',
    'raw_text': '''${HYPOTHESIS_TEXT}''',
}))
")")
echo "${WHISPER_RESPONSE}" | python3 -m json.tool
HYP_ID=$(echo "${WHISPER_RESPONSE}" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo ""

echo "4) Add second model transcription"
GEMINI_RESPONSE=$(curl -sf -X POST "${BASE_URL}/api/v1/transcription" \
  -H "Content-Type: application/json" \
  -d "$(python3 -c "
import json
print(json.dumps({
    'audio_guid': '${AUDIO_GUID}',
    'model_name': 'gemini-flash',
    'raw_text': 'سلام دنیا این یک متن تست بنچمارک است',
}))
")")
echo "${GEMINI_RESPONSE}" | python3 -m json.tool
GEMINI_ID=$(echo "${GEMINI_RESPONSE}" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo ""

echo "5) Compare reference vs whisper"
COMPARE1=$(curl -sf -X POST "${BASE_URL}/api/v1/compare" \
  -H "Content-Type: application/json" \
  -d "{\"ref_id\": ${REF_ID}, \"hyp_id\": ${HYP_ID}}")
echo "${COMPARE1}" | python3 -m json.tool
echo ""

echo "6) Compare reference vs gemini"
COMPARE2=$(curl -sf -X POST "${BASE_URL}/api/v1/compare" \
  -H "Content-Type: application/json" \
  -d "{\"ref_id\": ${REF_ID}, \"hyp_id\": ${GEMINI_ID}}")
echo "${COMPARE2}" | python3 -m json.tool
echo ""

echo "7) List all benchmarks for this audio"
curl -sf "${BASE_URL}/api/v1/benchmarks?audio_guid=${AUDIO_GUID}" | python3 -m json.tool
echo ""

echo "=== E2E Test PASSED ==="
echo "Admin panel: ${BASE_URL}/admin"
