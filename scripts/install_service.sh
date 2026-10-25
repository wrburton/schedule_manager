#!/usr/bin/env bash
# install_service.sh — install (or refresh) the calendar's user-level systemd unit.
#
# Run on the server as the app's user (linger is already enabled for it, which
# the other family apps rely on too):
#   bash ~/share/schedule_manager/scripts/install_service.sh
#
# Installs deploy/schedule_manager.service into ~/.config/systemd/user, makes
# .env readable by its owner only (it holds the Google refresh token), enables
# and (re)starts the unit, and health-checks it on 127.0.0.1:8000.
# The first run also stops and removes the old system-level unit
# (/etc/systemd/system/schedule_manager.service), which needs sudo: it asks for
# your password once, and keeps a copy of that unit in ~/backups. Safe to re-run.
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
UNIT=schedule_manager.service
UNIT_DIR="$HOME/.config/systemd/user"
SYSTEM_UNIT="/etc/systemd/system/$UNIT"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

[[ -f "$APP_DIR/.env" ]] && chmod 600 "$APP_DIR/.env" && echo "==> .env is now readable by $(id -un) only"

mkdir -p "$UNIT_DIR"
install -m 644 "$APP_DIR/deploy/$UNIT" "$UNIT_DIR/$UNIT"
echo "==> Installed $UNIT_DIR/$UNIT"
systemctl --user daemon-reload

if [[ -f "$SYSTEM_UNIT" ]]; then
  mkdir -p "$HOME/backups"
  cp "$SYSTEM_UNIT" "$HOME/backups/$UNIT.system-unit.$(date +%Y%m%d%H%M%S)"
  echo "==> Stopping and removing the old system unit $SYSTEM_UNIT (sudo; copy kept in ~/backups)"
  sudo systemctl disable --now "$UNIT"
  sudo rm "$SYSTEM_UNIT"
  sudo systemctl daemon-reload
fi

systemctl --user enable "$UNIT"
systemctl --user restart "$UNIT"

code=000
for _ in $(seq 1 30); do
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 http://127.0.0.1:8000/health || true)"
  [[ "$code" == 200 ]] && break
  sleep 1
done
systemctl --user --no-pager status "$UNIT" | head -5
if [[ "$code" == 200 ]]; then
  echo "==> $UNIT is healthy"
else
  journalctl --user -u "$UNIT" -n 40 --no-pager
  echo "!! $UNIT is not healthy (last HTTP status: $code)" >&2
  exit 1
fi
