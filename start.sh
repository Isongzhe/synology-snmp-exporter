#!/usr/bin/env bash
# Start the NAS monitoring API in the background
# Usage: ./start.sh [interval]  (default interval: 2s)
set -e

INTERVAL=${1:-2}
PID_FILE=".api.pid"
LOG_FILE="api.log"

if [ -f "$PID_FILE" ] && kill -0 "$(cat $PID_FILE)" 2>/dev/null; then
  echo "API is already running (PID $(cat $PID_FILE)). Run ./stop.sh first."
  exit 1
fi

echo "Starting NAS monitor API (SNMP_INTERVAL=${INTERVAL}s)..."
SNMP_INTERVAL=$INTERVAL uv run python api.py >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"
echo "Started. PID=$(cat $PID_FILE) | Logs: $LOG_FILE"
