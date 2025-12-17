#!/bin/bash

# Toggle cron enabled/disabled status
# Usage: ./toggle-cron.sh [enable|disable]

API_PORT=${API_PORT:-3001}
ENDPOINT="http://localhost:${API_PORT}/api/cron"

case "$1" in
  enable)
    echo "Enabling cron..."
    curl -X POST "${ENDPOINT}/enable" -H "Content-Type: application/json"
    ;;
  disable)
    echo "Disabling cron..."
    curl -X POST "${ENDPOINT}/disable" -H "Content-Type: application/json"
    ;;
  status)
    echo "Checking cron status..."
    curl -X GET "${ENDPOINT}/status" -H "Content-Type: application/json"
    ;;
  *)
    echo "Usage: $0 [enable|disable|status]"
    exit 1
    ;;
esac

