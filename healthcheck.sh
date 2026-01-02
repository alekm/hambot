#!/bin/sh
# Docker healthcheck script for hambot
# Verifies that the bot is running and connected to Discord

HEALTHCHECK_FILE="/app/config/healthcheck.json"
MAX_AGE=60  # Maximum age in seconds

# Check if healthcheck file exists
if [ ! -f "$HEALTHCHECK_FILE" ]; then
    echo "UNHEALTHY: Healthcheck file not found"
    exit 1
fi

# Read the healthcheck file
STATUS=$(cat "$HEALTHCHECK_FILE")

# Extract timestamp and status using basic tools (jq not available in slim image)
TIMESTAMP=$(echo "$STATUS" | grep -o '"timestamp": [0-9.]*' | grep -o '[0-9.]*')
BOT_STATUS=$(echo "$STATUS" | grep -o '"status": "[^"]*"' | grep -o '"[^"]*"$' | tr -d '"')

# Get current time
NOW=$(date +%s)

# Calculate age of healthcheck file
AGE=$((NOW - ${TIMESTAMP%.*}))

# Check if timestamp is too old
if [ "$AGE" -gt "$MAX_AGE" ]; then
    echo "UNHEALTHY: Heartbeat too old (${AGE}s > ${MAX_AGE}s)"
    exit 1
fi

# Check if bot is connected
if [ "$BOT_STATUS" != "connected" ]; then
    echo "UNHEALTHY: Bot status is $BOT_STATUS"
    exit 1
fi

echo "HEALTHY: Bot connected, heartbeat ${AGE}s old"
exit 0
