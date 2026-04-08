#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PATH_RESOLVER="$ROOT_DIR/tools/resolve_instance_path.py"
eval "$(/usr/bin/python3 "$PATH_RESOLVER" --shell)"
PID_FILE="$WEB_RUNTIME_DIR/bio-digest-web-tunnel.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "Tunnel pid file not found"
  exit 1
fi

PID="$(cat "$PID_FILE")"
if kill -0 "$PID" >/dev/null 2>&1; then
  kill "$PID"
fi
rm -f "$PID_FILE"
echo "Stopped Cloudflare Tunnel"
