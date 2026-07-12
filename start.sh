#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
PATH_RESOLVER="$ROOT_DIR/tools/resolve_instance_path.py"
DETACHER="$ROOT_DIR/tools/launch_detached.py"
SIGNATURE_TOOL="$ROOT_DIR/tools/compute_launch_signature.py"
ENABLE_TUNNEL_OVERRIDE="${ENABLE_TUNNEL-}"
eval "$(/usr/bin/python3 "$PATH_RESOLVER" --shell)"

RUNTIME_DIR="$WEB_RUNTIME_DIR"
CONFIG_FILE="$WEB_DEPLOY_ENV_FILE"
BACKEND_PID_FILE="$RUNTIME_DIR/backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"
TUNNEL_PID_FILE="$RUNTIME_DIR/tunnel.pid"
ARCHIVE_SYNC_PID_FILE="$RUNTIME_DIR/archive-sync.pid"
BACKEND_LOG="$RUNTIME_DIR/backend.log"
FRONTEND_LOG="$RUNTIME_DIR/frontend.log"
TUNNEL_LOG="$RUNTIME_DIR/tunnel.log"
ARCHIVE_SYNC_LOG="$RUNTIME_DIR/archive-sync.log"
BACKEND_PYTHON="$BACKEND_DIR/.venv/bin/python"
BACKEND_UVICORN="$BACKEND_DIR/.venv/bin/uvicorn"
ARCHIVE_SYNC_SCRIPT="$BACKEND_DIR/sync_archives.py"
TUNNEL_CONFIG_FILE="$WEB_TUNNEL_CONFIG_FILE"
CLOUDFLARED_BIN="${CLOUDFLARED_BIN:-}"
BACKEND_META_FILE="$RUNTIME_DIR/backend.meta"
FRONTEND_META_FILE="$RUNTIME_DIR/frontend.meta"
ARCHIVE_SYNC_META_FILE="$RUNTIME_DIR/archive-sync.meta"

mkdir -p "$RUNTIME_DIR" "$WEB_DATA_DIR"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Missing deploy config. Copy the template under bio-literature-config/env/web first." >&2
  exit 1
fi

if [[ ! -x "$BACKEND_UVICORN" ]]; then
  echo "Backend virtualenv is missing. Create backend/.venv and install requirements first." >&2
  exit 1
fi

if [[ ! -x "$BACKEND_PYTHON" ]]; then
  echo "Backend Python is missing. Create backend/.venv and install requirements first." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is not available in PATH." >&2
  exit 1
fi

if [[ ! -x "$DETACHER" ]]; then
  echo "Detached launcher is missing from tools/." >&2
  exit 1
fi

if [[ ! -x "$SIGNATURE_TOOL" ]]; then
  echo "Launch signature tool is missing from tools/." >&2
  exit 1
fi

set -a
source "$CONFIG_FILE"
set +a

if [[ -n "$ENABLE_TUNNEL_OVERRIDE" ]]; then
  ENABLE_TUNNEL="$ENABLE_TUNNEL_OVERRIDE"
fi

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    echo "Missing required setting: $key" >&2
    exit 1
  fi
}

is_enabled() {
  local raw_value="${1,,}"
  [[ "$raw_value" == "1" || "$raw_value" == "true" || "$raw_value" == "yes" || "$raw_value" == "on" ]]
}

require_env "APP_HOSTNAME"
require_env "BACKEND_HOST"
require_env "BACKEND_PORT"
require_env "FRONTEND_HOST"
require_env "FRONTEND_PORT"
require_env "LOCAL_FRONTEND_ORIGIN"
require_env "DATABASE_URL"
require_env "SESSION_SECRET"
require_env "FRONTEND_ORIGIN"
require_env "WEB_BASE_URL"
require_env "INITIAL_ADMIN_EMAIL"

SESSION_COOKIE_SECURE="${SESSION_COOKIE_SECURE:-false}"
INITIAL_ADMIN_NAME="${INITIAL_ADMIN_NAME:-Admin}"
BOOTSTRAP_ADMIN="${BOOTSTRAP_ADMIN:-true}"
DATA_RETENTION_DAYS="${DATA_RETENTION_DAYS:-30}"
RESERVED_PORT_RANGE="${RESERVED_PORT_RANGE:-}"
ENABLE_TUNNEL="${ENABLE_TUNNEL:-true}"
ENABLE_PRODUCER_SYNC_DAEMON="${ENABLE_PRODUCER_SYNC_DAEMON:-true}"
PRODUCER_SYNC_INTERVAL_SECONDS="${PRODUCER_SYNC_INTERVAL_SECONDS:-60}"
PRODUCER_SYNC_WINDOW_START="${PRODUCER_SYNC_WINDOW_START:-08:00}"
PRODUCER_SYNC_WINDOW_END="${PRODUCER_SYNC_WINDOW_END:-09:00}"

if [[ "$DATABASE_URL" == sqlite:///./* ]]; then
  DATABASE_URL="sqlite:///$WEB_DATA_DIR/${DATABASE_URL#sqlite:///./}"
fi

ensure_allowed_port() {
  local label="$1"
  local port="$2"

  if [[ -z "$RESERVED_PORT_RANGE" ]]; then
    return
  fi

  local range_start="${RESERVED_PORT_RANGE%-*}"
  local range_end="${RESERVED_PORT_RANGE#*-}"
  if [[ "$range_start" =~ ^[0-9]+$ ]] && [[ "$range_end" =~ ^[0-9]+$ ]] && [[ "$port" =~ ^[0-9]+$ ]]; then
    if (( port >= range_start && port <= range_end )); then
      echo "$label port falls inside reserved range $RESERVED_PORT_RANGE." >&2
      exit 1
    fi
  fi
}

start_backend() {
  echo "Starting backend on configured loopback address"
  "$DETACHER" \
    --cwd "$BACKEND_DIR" \
    --stdout "$BACKEND_LOG" \
    --pid-file "$BACKEND_PID_FILE" \
    --env "DATABASE_URL=$DATABASE_URL" \
    --env "FRONTEND_ORIGIN=$LOCAL_FRONTEND_ORIGIN" \
    --env "SESSION_SECRET=$SESSION_SECRET" \
    --env "SESSION_COOKIE_SECURE=$SESSION_COOKIE_SECURE" \
    --env "WEB_BASE_URL=$WEB_BASE_URL" \
    --env "INITIAL_ADMIN_EMAIL=$INITIAL_ADMIN_EMAIL" \
    --env "INITIAL_ADMIN_NAME=$INITIAL_ADMIN_NAME" \
    --env "BOOTSTRAP_ADMIN=$BOOTSTRAP_ADMIN" \
    --env "DATA_RETENTION_DAYS=$DATA_RETENTION_DAYS" \
    --env "PRODUCER_SYNC_INTERVAL_SECONDS=0" \
    -- "$BACKEND_UVICORN" app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
}

start_frontend() {
  echo "Building frontend production assets"
  (
    cd "$FRONTEND_DIR"
    VITE_APP_HOSTNAME="$APP_HOSTNAME" \
      VITE_API_PROXY_TARGET="http://${BACKEND_HOST}:${BACKEND_PORT}" \
      npm run build
  ) >> "$FRONTEND_LOG" 2>&1
  echo "Starting frontend production preview on configured loopback address"
  "$DETACHER" \
    --cwd "$FRONTEND_DIR" \
    --stdout "$FRONTEND_LOG" \
    --pid-file "$FRONTEND_PID_FILE" \
    --env "VITE_APP_HOSTNAME=$APP_HOSTNAME" \
    --env "VITE_HOST=$FRONTEND_HOST" \
    --env "VITE_PORT=$FRONTEND_PORT" \
    --env "VITE_API_PROXY_TARGET=http://${BACKEND_HOST}:${BACKEND_PORT}" \
    -- npm run preview -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" --strictPort
}

start_archive_sync() {
  if [[ ! -f "$ARCHIVE_SYNC_SCRIPT" ]]; then
    echo "Producer sync daemon is missing: $ARCHIVE_SYNC_SCRIPT" >&2
    exit 1
  fi

  if ! is_enabled "$ENABLE_PRODUCER_SYNC_DAEMON"; then
    echo "Producer sync daemon disabled by config"
    return
  fi

  echo "Starting producer sync daemon"
  "$DETACHER" \
    --cwd "$BACKEND_DIR" \
    --stdout "$ARCHIVE_SYNC_LOG" \
    --pid-file "$ARCHIVE_SYNC_PID_FILE" \
    --env "DATABASE_URL=$DATABASE_URL" \
    --env "PRODUCER_SYNC_ENABLED=true" \
    --env "PRODUCER_SYNC_INTERVAL_SECONDS=$PRODUCER_SYNC_INTERVAL_SECONDS" \
    --env "PRODUCER_SYNC_WINDOW_START=$PRODUCER_SYNC_WINDOW_START" \
    --env "PRODUCER_SYNC_WINDOW_END=$PRODUCER_SYNC_WINDOW_END" \
    -- "$BACKEND_PYTHON" "$ARCHIVE_SYNC_SCRIPT" --interval-seconds "$PRODUCER_SYNC_INTERVAL_SECONDS"
}

start_tunnel() {
  if ! is_enabled "$ENABLE_TUNNEL"; then
    echo "Tunnel disabled by config"
    return
  fi

  if [[ ! -f "$TUNNEL_CONFIG_FILE" ]]; then
    echo "Missing tunnel config. Copy the template under bio-literature-config/tunnel/web first, or set ENABLE_TUNNEL=false." >&2
    exit 1
  fi

  if [[ -z "$CLOUDFLARED_BIN" ]]; then
    CLOUDFLARED_BIN="$(command -v cloudflared || true)"
  fi

  if [[ -z "$CLOUDFLARED_BIN" || ! -x "$CLOUDFLARED_BIN" ]]; then
    echo "cloudflared is not available. Install it, set CLOUDFLARED_BIN, or set ENABLE_TUNNEL=false." >&2
    exit 1
  fi

  if [[ -f "$TUNNEL_PID_FILE" ]] && kill -0 "$(cat "$TUNNEL_PID_FILE")" >/dev/null 2>&1; then
    echo "Tunnel already running"
    return
  fi

  echo "Starting Cloudflare Tunnel for configured hostname"
  "$DETACHER" \
    --cwd "$(dirname "$TUNNEL_CONFIG_FILE")" \
    --stdout "$TUNNEL_LOG" \
    --pid-file "$TUNNEL_PID_FILE" \
    -- "$CLOUDFLARED_BIN" tunnel --config "$TUNNEL_CONFIG_FILE" run
}

service_signature() {
  local service="$1"
  shift
  /usr/bin/python3 "$SIGNATURE_TOOL" --root "$ROOT_DIR" --service "$service" "$@"
}

stop_pid_file_if_running() {
  local label="$1"
  local pid_file="$2"

  if [[ ! -f "$pid_file" ]]; then
    return
  fi

  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "Restarting $label to apply updated code/config"
    kill -- "-$pid" >/dev/null 2>&1 || kill "$pid" >/dev/null 2>&1 || true
    for _ in {1..20}; do
      if ! kill -0 "$pid" >/dev/null 2>&1; then
        break
      fi
      sleep 0.2
    done
  fi

  rm -f "$pid_file"
}

ensure_service() {
  local label="$1"
  local pid_file="$2"
  local meta_file="$3"
  local signature="$4"
  local starter="$5"

  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" >/dev/null 2>&1; then
    local existing_signature=""
    if [[ -f "$meta_file" ]]; then
      existing_signature="$(cat "$meta_file")"
    fi
    if [[ "$existing_signature" == "$signature" ]]; then
      echo "$label already running"
      return
    fi
    stop_pid_file_if_running "$label" "$pid_file"
  else
    rm -f "$pid_file"
  fi

  "$starter"
  printf '%s\n' "$signature" > "$meta_file"
}

ensure_allowed_port "Backend" "$BACKEND_PORT"
ensure_allowed_port "Frontend" "$FRONTEND_PORT"

BACKEND_SIGNATURE="$(service_signature backend \
  --salt "BACKEND_HOST=$BACKEND_HOST" \
  --salt "BACKEND_PORT=$BACKEND_PORT" \
  --salt "DATABASE_URL=$DATABASE_URL" \
  --salt "LOCAL_FRONTEND_ORIGIN=$LOCAL_FRONTEND_ORIGIN" \
  --salt "WEB_BASE_URL=$WEB_BASE_URL" \
  --salt "DATA_RETENTION_DAYS=$DATA_RETENTION_DAYS")"
FRONTEND_SIGNATURE="$(service_signature frontend \
  --salt "APP_HOSTNAME=$APP_HOSTNAME" \
  --salt "FRONTEND_HOST=$FRONTEND_HOST" \
  --salt "FRONTEND_PORT=$FRONTEND_PORT" \
  --salt "BACKEND_HOST=$BACKEND_HOST" \
  --salt "BACKEND_PORT=$BACKEND_PORT")"
ARCHIVE_SYNC_SIGNATURE="$(service_signature archive-sync \
  --salt "DATABASE_URL=$DATABASE_URL" \
  --salt "PRODUCER_SYNC_INTERVAL_SECONDS=$PRODUCER_SYNC_INTERVAL_SECONDS" \
  --salt "PRODUCER_SYNC_WINDOW_START=$PRODUCER_SYNC_WINDOW_START" \
  --salt "PRODUCER_SYNC_WINDOW_END=$PRODUCER_SYNC_WINDOW_END" \
  --salt "ENABLE_PRODUCER_SYNC_DAEMON=$ENABLE_PRODUCER_SYNC_DAEMON")"

ensure_service "Backend" "$BACKEND_PID_FILE" "$BACKEND_META_FILE" "$BACKEND_SIGNATURE" start_backend
ensure_service "Frontend" "$FRONTEND_PID_FILE" "$FRONTEND_META_FILE" "$FRONTEND_SIGNATURE" start_frontend
ensure_service "Producer sync daemon" "$ARCHIVE_SYNC_PID_FILE" "$ARCHIVE_SYNC_META_FILE" "$ARCHIVE_SYNC_SIGNATURE" start_archive_sync
start_tunnel

echo "Local web services are running"
