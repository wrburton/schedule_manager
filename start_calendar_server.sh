#!/usr/bin/env bash
# Start the Calendar Checklist server.
#
# TLS is now terminated by Caddy; this process runs plain HTTP on localhost.
#
# Usage:
#   ./start_calendar_server.sh
#
# Environment variables:
#   HOST       - Bind address (default: 127.0.0.1)
#   PORT       - Server port (default: 8000)
#   ROOT_PATH  - ASGI root path for reverse proxy prefix (default: /schedule)
#   VENV_PATH  - Path to virtualenv (default: ./venv)

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
ROOT_PATH="${ROOT_PATH:-/schedule}"
VENV_PATH="${VENV_PATH:-$APP_DIR/venv}"

if [[ -d "$VENV_PATH" ]]; then
    # shellcheck disable=SC1090
    source "$VENV_PATH/bin/activate"
    echo "Using virtualenv at $VENV_PATH"
else
    echo "No virtualenv detected at $VENV_PATH; using global environment."
fi

cd "$APP_DIR"

echo "Starting Calendar Checklist on http://$HOST:$PORT (root-path: $ROOT_PATH)"
exec python3 -m uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --root-path "$ROOT_PATH" \
    --reload
