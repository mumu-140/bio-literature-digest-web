#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PATH_RESOLVER="$ROOT_DIR/tools/resolve_instance_path.py"
eval "$(/usr/bin/python3 "$PATH_RESOLVER" --shell)"
RUNTIME_DIR="$WEB_RUNTIME_DIR"

stop_by_pid_file() {
  local label="$1"
  local pid_file="$2"

  if [[ ! -f "$pid_file" ]]; then
    echo "$label pid file not found: $pid_file"
    return
  fi

  local pid
  pid="$(cat "$pid_file")"

  if kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid"
    echo "Stopped $label"
  else
    echo "$label already stopped"
  fi

  rm -f "$pid_file"
}

stop_by_pid_file "frontend" "$RUNTIME_DIR/frontend.pid"
stop_by_pid_file "backend" "$RUNTIME_DIR/backend.pid"
