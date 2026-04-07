#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
PATH_RESOLVER="$ROOT_DIR/tools/resolve_instance_path.py"
eval "$(/usr/bin/python3 "$PATH_RESOLVER" --shell)"
RUNTIME_DIR="$WEB_RUNTIME_DIR"
CONFIG_FILE="$WEB_DEPLOY_ENV_FILE"
BACKEND_PID_FILE="$RUNTIME_DIR/backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"
BACKEND_LOG="$RUNTIME_DIR/backend.log"
FRONTEND_BUILD_LOG="$RUNTIME_DIR/frontend-build.log"
FRONTEND_LOG="$RUNTIME_DIR/frontend.log"
BACKEND_UVICORN="$BACKEND_DIR/.venv/bin/uvicorn"
DETACHER="$ROOT_DIR/tools/launch_detached.py"
mkdir -p "$RUNTIME_DIR"

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Missing deploy config: $CONFIG_FILE" >&2
  exit 1
fi

if [[ ! -x "$BACKEND_UVICORN" ]]; then
  echo "Missing backend uvicorn binary: $BACKEND_UVICORN" >&2
  echo "Create the backend venv and install requirements first." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found in PATH" >&2
  exit 1
fi

if [[ ! -x "$DETACHER" ]]; then
  echo "Detached launcher not found: $DETACHER" >&2
  exit 1
fi

set -a
source "$CONFIG_FILE"
set +a

APP_HOSTNAME="${APP_HOSTNAME:-localhost}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8602}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-8601}"
LOCAL_FRONTEND_ORIGIN="${LOCAL_FRONTEND_ORIGIN:-http://${FRONTEND_HOST}:${FRONTEND_PORT}}"
SESSION_COOKIE_SECURE="${SESSION_COOKIE_SECURE:-false}"

if [[ "${DATABASE_URL:-}" == sqlite:///./* ]]; then
  DATABASE_URL="sqlite:///$WEB_DATA_DIR/${DATABASE_URL#sqlite:///./}"
fi

ensure_allowed_port() {
  local label="$1"
  local port="$2"

  if [[ "$port" =~ ^[0-9]+$ ]] && (( port >= 8000 && port <= 8200 )); then
    echo "$label port $port is forbidden. Use ports outside 8000-8200." >&2
    exit 1
  fi
}

ensure_allowed_port "Backend" "$BACKEND_PORT"
ensure_allowed_port "Frontend" "$FRONTEND_PORT"

start_backend() {
  if [[ -f "$BACKEND_PID_FILE" ]] && kill -0 "$(cat "$BACKEND_PID_FILE")" >/dev/null 2>&1; then
    echo "Backend already running"
    return
  fi

  echo "Starting backend on ${BACKEND_HOST}:${BACKEND_PORT}"
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
    --env "INITIAL_ADMIN_PASSWORD=$INITIAL_ADMIN_PASSWORD" \
    --env "INITIAL_ADMIN_NAME=${INITIAL_ADMIN_NAME:-Admin}" \
    --env "BOOTSTRAP_ADMIN=${BOOTSTRAP_ADMIN:-true}" \
    --env "DATA_RETENTION_DAYS=${DATA_RETENTION_DAYS:-30}" \
    -- "$BACKEND_UVICORN" app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
}

start_frontend() {
  if [[ -f "$FRONTEND_PID_FILE" ]] && kill -0 "$(cat "$FRONTEND_PID_FILE")" >/dev/null 2>&1; then
    echo "Frontend already running"
    return
  fi

  echo "Starting frontend dev server on ${FRONTEND_HOST}:${FRONTEND_PORT}"
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

start_backend
start_frontend

echo "Local web processes are running"
