#!/usr/bin/env bash
# Stop the NAS monitoring API
PID_FILE=".api.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "No PID file found. Is the API running?"
  exit 1
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
  kill "$PID"
  rm "$PID_FILE"
  echo "Stopped API (PID $PID)"
else
  echo "Process $PID not found (already stopped?)"
  rm "$PID_FILE"
fi
