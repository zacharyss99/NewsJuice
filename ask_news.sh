#!/bin/bash

# NewsJuice Pipeline Query Script
# Usage: ./ask_news.sh "Your question here"

if [ $# -eq 0 ]; then
    echo "Usage: $0 \"Your question here\""
    echo "Example: $0 \"Show me the News from Harvard Gazette\""
    exit 1
fi

QUERY="$1"
USER_ID="${USER_ID:-default_user}"

echo "🔍 Querying NewsJuice Pipeline..."
echo "📝 Question: $QUERY"
echo "👤 User: $USER_ID"
echo ""

# Make the API call
docker compose exec manager curl -s -X POST "http://localhost:8000/ask" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"$USER_ID\", \"query\": \"$QUERY\"}" | \
  python3 -m json.tool

echo ""
echo "✅ Query completed!"
