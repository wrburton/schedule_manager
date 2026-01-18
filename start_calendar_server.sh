#!/usr/bin/env bash
# Start the Calendar Checklist server with SSL.
#
# Usage:
#   ./start_calendar_server.sh
#
# Environment variables:
#   HOST       - Bind address (default: 0.0.0.0)
#   PORT       - Server port (default: 8000)
#   VENV_PATH  - Path to virtualenv (default: ./venv)
#
# Requires SSL certificates (cert.pem and key.pem) in the project directory.
# Generate with:
#   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
VENV_PATH="${VENV_PATH:-$APP_DIR/venv}"

# Activate virtualenv if present
if [[ -d "$VENV_PATH" ]]; then
    # shellcheck disable=SC1090
    source "$VENV_PATH/bin/activate"
    echo "Using virtualenv at $VENV_PATH"
else
    echo "No virtualenv detected at $VENV_PATH; using global environment."
fi

cd "$APP_DIR"

# Check for SSL certificates
if [[ ! -f "cert.pem" || ! -f "key.pem" ]]; then
    echo "Error: SSL certificates not found."
    echo ""
    echo "Generate self-signed certificates with:"
    echo "  openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes"
    exit 1
fi

echo "Starting Calendar Checklist on https://$HOST:$PORT"
exec python3 -m uvicorn app.main:app --host "$HOST" --port "$PORT" --ssl-keyfile key.pem --ssl-certfile cert.pem --reload
