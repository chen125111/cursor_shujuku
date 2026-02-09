#!/usr/bin/env bash
set -euo pipefail

PID_FILE="${PID_FILE:-/tmp/cursor_shujuku_uvicorn.pid}"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No PID file found at $PID_FILE"
  exit 1
fi

PID="$(cat "$PID_FILE")"
if [[ -z "$PID" ]]; then
  echo "PID file is empty"
  exit 1
fi

if kill "$PID" >/dev/null 2>&1; then
  rm -f "$PID_FILE"
  echo "Stopped server (PID $PID)"
else
  echo "Failed to stop server (PID $PID)"
  exit 1
fi
