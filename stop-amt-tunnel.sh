#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PATH_RESOLVER="$ROOT_DIR/tools/resolve_instance_path.py"
eval "$(/usr/bin/python3 "$PATH_RESOLVER" --shell)"
PID_FILE="$WEB_RUNTIME_DIR/amt-bio-digest-tunnel.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No tunnel pid file found: $PID_FILE" >&2
  exit 1
fi

PID="$(cat "$PID_FILE")"
kill "$PID"
rm -f "$PID_FILE"
echo "Stopped Cloudflare Tunnel"
