#!/bin/zsh

set -euo pipefail

PID_FILE="$(cd "$(dirname "$0")" && pwd)/.runtime/amt-bio-digest-tunnel.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No tunnel pid file found: $PID_FILE" >&2
  exit 1
fi

PID="$(cat "$PID_FILE")"
kill "$PID"
rm -f "$PID_FILE"
echo "Stopped Cloudflare Tunnel"
