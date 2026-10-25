#!/usr/bin/env bash
# Build app/static/css/app.css from app/static/css/src/app.css with the pinned Tailwind CLI
# (the family apps' script; this app keeps its static files under app/).
#
# Runs on the server: pre-receive builds into the temporary export (a broken
# build rejects the push); post-receive builds into the live tree. The output
# is gitignored, so it is never committed and can't go stale.
#
# Usage: scripts/build_css.sh [APP_DIR]   (default: this repository)
#
# The CLI is the standalone binary for the pinned version, installed once
# outside the repository:
#   V=4.3.3; D=~/.local/share/tailwindcss/$V; mkdir -p $D && cd $D
#   curl -fsSLO https://github.com/tailwindlabs/tailwindcss/releases/download/v$V/tailwindcss-linux-x64
#   curl -fsSLO https://github.com/tailwindlabs/tailwindcss/releases/download/v$V/sha256sums.txt
#   grep ' ./tailwindcss-linux-x64$' sha256sums.txt | sed 's| ./| |' | sha256sum -c - \
#     && mv tailwindcss-linux-x64 tailwindcss && chmod 755 tailwindcss
# Upgrading: install the new version, change TAILWIND_VERSION, push.
set -euo pipefail

TAILWIND_VERSION="4.3.3"
APP_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
BIN="${TAILWIND_BIN:-$HOME/.local/share/tailwindcss/$TAILWIND_VERSION/tailwindcss}"
SRC="$APP_DIR/app/static/css/src/app.css"
OUT="$APP_DIR/app/static/css/app.css"

if [[ ! -x "$BIN" ]]; then
  echo "Tailwind CLI $TAILWIND_VERSION not found at $BIN — see the install steps in $0" >&2
  exit 1
fi
if [[ ! -f "$SRC" ]]; then
  echo "No CSS source at $SRC — nothing to build"
  exit 0
fi

# Build next to the output and rename, so the server never serves a half-written file.
# Not minified: the minifier rewrites some declarations, and the plain output is
# readable when debugging on the server, for a few KB more.
"$BIN" --input "$SRC" --output "$OUT.tmp" --cwd "$APP_DIR"
mv "$OUT.tmp" "$OUT"
echo "Built $OUT ($(wc -c <"$OUT") bytes) with Tailwind $TAILWIND_VERSION"
