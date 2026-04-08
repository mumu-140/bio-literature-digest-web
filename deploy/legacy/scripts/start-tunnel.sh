#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PATH_RESOLVER="$ROOT_DIR/tools/resolve_instance_path.py"
eval "$(/usr/bin/python3 "$PATH_RESOLVER" --shell)"
CONFIG_FILE="$WEB_TUNNEL_CONFIG_FILE"
PID_FILE="$WEB_RUNTIME_DIR/bio-digest-web-tunnel.pid"
CONFIG_DIR="$(dirname "$CONFIG_FILE")"
CLOUDFLARED_BIN="${CLOUDFLARED_BIN:-}"

mkdir -p "$WEB_RUNTIME_DIR"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Missing tunnel config. Copy the template under bio-literature-config/tunnel/web first." >&2
  exit 1
fi

if [[ -z "$CLOUDFLARED_BIN" ]]; then
  CLOUDFLARED_BIN="$(command -v cloudflared || true)"
fi

if [[ -z "$CLOUDFLARED_BIN" || ! -x "$CLOUDFLARED_BIN" ]]; then
  echo "cloudflared is not available. Install it or set CLOUDFLARED_BIN." >&2
  exit 1
fi

echo "Starting Cloudflare Tunnel for configured hostname"
cd "$CONFIG_DIR"
exec "$CLOUDFLARED_BIN" tunnel --config "$CONFIG_FILE" --pidfile "$PID_FILE" run
