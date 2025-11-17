#!/bin/bash
# Script to create admin user and token
# Make sure the service is running on http://localhost:8080

echo "Creating admin user..."
USER_RESPONSE=$(curl -s -X POST http://localhost:8080/admin/auth/users \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","email":"admin@example.com"}')

echo "User response: $USER_RESPONSE"

# Extract user_id from response (assuming JSON format: {"success":true,"user_id":1,"message":"..."})
USER_ID=$(echo $USER_RESPONSE | grep -o '"user_id":[0-9]*' | grep -o '[0-9]*')

if [ -z "$USER_ID" ]; then
  echo "Failed to create user or extract user_id. Response: $USER_RESPONSE"
  exit 1
fi

echo "User created with ID: $USER_ID"
echo ""
echo "Creating token..."

# Calculate expiration date: 10 years from now (large number as requested)
# Format: YYYY-MM-DDTHH:MM:SS
EXPIRES_AT=$(date -u -d "+10 years" +"%Y-%m-%dT%H:%M:%S" 2>/dev/null || date -u -v+10y +"%Y-%m-%dT%H:%M:%S" 2>/dev/null || echo "")

if [ -z "$EXPIRES_AT" ]; then
  # Fallback: use a far future date manually
  EXPIRES_AT="2099-12-31T23:59:59"
fi

TOKEN_RESPONSE=$(curl -s -X POST http://localhost:8080/admin/auth/tokens \
  -H "Content-Type: application/json" \
  -d "{\"user_id\":$USER_ID,\"name\":\"Main Development Token\",\"rate_limit_per_day\":1000,\"expires_at\":\"$EXPIRES_AT\"}")

echo "Token response: $TOKEN_RESPONSE"

# Extract token from response
TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
  echo "Failed to extract token. Full response: $TOKEN_RESPONSE"
  exit 1
fi

echo ""
echo "=========================================="
echo "Token created successfully!"
echo "=========================================="
echo "Token: $TOKEN"
echo ""
echo "Add this to your .env file:"
echo "API_TOKEN=$TOKEN"
echo "=========================================="

