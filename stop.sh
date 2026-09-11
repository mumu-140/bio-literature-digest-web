#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PATH_RESOLVER="$ROOT_DIR/tools/resolve_instance_path.py"
eval "$(/usr/bin/python3 "$PATH_RESOLVER" --shell)"
RUNTIME_DIR="$WEB_RUNTIME_DIR"

stop_by_pid_file() {
  local label="$1"
  local pid_file="$2"
  local meta_file="$3"

  if [[ ! -f "$pid_file" ]]; then
    echo "$label pid file not found"
    rm -f "$meta_file"
    return
  fi

  local pid
  pid="$(cat "$pid_file")"

  if kill -0 "$pid" >/dev/null 2>&1; then
    kill -- "-$pid" >/dev/null 2>&1 || kill "$pid"
    echo "Stopped $label"
  else
    echo "$label already stopped"
  fi

  rm -f "$pid_file"
  rm -f "$meta_file"
}

stop_by_pid_file "tunnel" "$RUNTIME_DIR/tunnel.pid" "$RUNTIME_DIR/tunnel.meta"
stop_by_pid_file "archive-sync" "$RUNTIME_DIR/archive-sync.pid" "$RUNTIME_DIR/archive-sync.meta"
stop_by_pid_file "frontend" "$RUNTIME_DIR/frontend.pid" "$RUNTIME_DIR/frontend.meta"
stop_by_pid_file "backend" "$RUNTIME_DIR/backend.pid" "$RUNTIME_DIR/backend.meta"
