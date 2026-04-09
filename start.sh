#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
PATH_RESOLVER="$ROOT_DIR/tools/resolve_instance_path.py"
DETACHER="$ROOT_DIR/tools/launch_detached.py"
ENABLE_TUNNEL_OVERRIDE="${ENABLE_TUNNEL-}"
eval "$(/usr/bin/python3 "$PATH_RESOLVER" --shell)"

RUNTIME_DIR="$WEB_RUNTIME_DIR"
CONFIG_FILE="$WEB_DEPLOY_ENV_FILE"
BACKEND_PID_FILE="$RUNTIME_DIR/backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"
TUNNEL_PID_FILE="$RUNTIME_DIR/tunnel.pid"
BACKEND_LOG="$RUNTIME_DIR/backend.log"
FRONTEND_LOG="$RUNTIME_DIR/frontend.log"
TUNNEL_LOG="$RUNTIME_DIR/tunnel.log"
BACKEND_PYTHON="$BACKEND_DIR/.venv/bin/python"
BACKEND_UVICORN="$BACKEND_DIR/.venv/bin/uvicorn"
TUNNEL_CONFIG_FILE="$WEB_TUNNEL_CONFIG_FILE"
CLOUDFLARED_BIN="${CLOUDFLARED_BIN:-}"

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

set -a
source "$CONFIG_FILE"
set +a

if [[ -n "$ENABLE_TUNNEL_OVERRIDE" ]]; then
  ENABLE_TUNNEL="$ENABLE_TUNNEL_OVERRIDE"
fi

require_env() {
  local key="$1"
  if [[ -z "${(P)key:-}" ]]; then
    echo "Missing required setting: $key" >&2
    exit 1
  fi
}

is_enabled() {
  local raw_value="${1:l}"
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
  if [[ -f "$BACKEND_PID_FILE" ]] && kill -0 "$(cat "$BACKEND_PID_FILE")" >/dev/null 2>&1; then
    echo "Backend already running"
    return
  fi

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
    -- "$BACKEND_UVICORN" app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
}

start_frontend() {
  if [[ -f "$FRONTEND_PID_FILE" ]] && kill -0 "$(cat "$FRONTEND_PID_FILE")" >/dev/null 2>&1; then
    echo "Frontend already running"
    return
  fi

  echo "Starting frontend dev server on configured loopback address"
  "$DETACHER" \
    --cwd "$FRONTEND_DIR" \
    --stdout "$FRONTEND_LOG" \
    --pid-file "$FRONTEND_PID_FILE" \
    --env "VITE_APP_HOSTNAME=$APP_HOSTNAME" \
    --env "VITE_HOST=$FRONTEND_HOST" \
    --env "VITE_PORT=$FRONTEND_PORT" \
    --env "VITE_API_PROXY_TARGET=http://${BACKEND_HOST}:${BACKEND_PORT}" \
    -- npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT"
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

ensure_allowed_port "Backend" "$BACKEND_PORT"
ensure_allowed_port "Frontend" "$FRONTEND_PORT"

start_backend
start_frontend
start_tunnel

echo "Local web services are running"
