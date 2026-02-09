#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-8001}"
PID_FILE="${PID_FILE:-/tmp/cursor_shujuku_uvicorn.pid}"

export DATABASE_URL="${DATABASE_URL:-mysql://root@127.0.0.1:3306/gas_data}"
export SECURITY_DATABASE_URL="${SECURITY_DATABASE_URL:-mysql://root@127.0.0.1:3306/security_data}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"
export SECRET_KEY="${SECRET_KEY:-local-test-secret}"

if [[ "${USE_SQLITE:-0}" == "1" ]]; then
  export DATABASE_URL=""
  export SECURITY_DATABASE_URL=""
fi

python3 -m uvicorn backend.main:app --host 127.0.0.1 --port "$PORT" >/tmp/uvicorn_"$PORT".log 2>&1 &
echo $! > "$PID_FILE"
echo "Server started: http://127.0.0.1:${PORT}/admin"
echo "PID: $(cat "$PID_FILE") (log: /tmp/uvicorn_${PORT}.log)"
