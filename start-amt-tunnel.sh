#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="$ROOT_DIR/bio-literature-config/web/cloudflare-tunnel/config.yml"
PID_FILE="$ROOT_DIR/.runtime/amt-bio-digest-tunnel.pid"
CLOUDFLARED_BIN="${CLOUDFLARED_BIN:-/opt/homebrew/bin/cloudflared}"
CONFIG_DIR="$(dirname "$CONFIG_FILE")"

mkdir -p "$ROOT_DIR/.runtime"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Missing Cloudflare Tunnel config: $CONFIG_FILE" >&2
  echo "Copy deploy/cloudflare-tunnel/config.yml.example into $ROOT_DIR/bio-literature-config/web/cloudflare-tunnel/config.yml first." >&2
  exit 1
fi

if [[ ! -x "$CLOUDFLARED_BIN" ]]; then
  echo "cloudflared binary not found: $CLOUDFLARED_BIN" >&2
  exit 1
fi

echo "Starting Cloudflare Tunnel for configured hostname"
cd "$CONFIG_DIR"
exec "$CLOUDFLARED_BIN" tunnel --config "$CONFIG_FILE" --pidfile "$PID_FILE" run
