#!/bin/bash

# Manually trigger a job execution
# Usage: ./run-job.sh

API_PORT=${API_PORT:-3001}
ENDPOINT="http://localhost:${API_PORT}/api/job/run"

echo "Triggering manual job execution..."
curl -X POST "${ENDPOINT}" -H "Content-Type: application/json"

