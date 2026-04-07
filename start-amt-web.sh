#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUNTIME_DIR="$ROOT_DIR/.runtime"
CONFIG_FILE="$ROOT_DIR/bio-literature-config/web/deploy.env.local"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BACKEND_PID_FILE="$RUNTIME_DIR/backend.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"
BACKEND_LOG="$RUNTIME_DIR/backend.log"
FRONTEND_BUILD_LOG="$RUNTIME_DIR/frontend-build.log"
FRONTEND_LOG="$RUNTIME_DIR/frontend.log"
BACKEND_UVICORN="$BACKEND_DIR/.venv/bin/uvicorn"

cd "$ROOT_DIR"
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

set -a
source "$CONFIG_FILE"
set +a

APP_HOSTNAME="${APP_HOSTNAME:-localhost}"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8602}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-8601}"

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
  nohup env \
    DATABASE_URL="$DATABASE_URL" \
    FRONTEND_ORIGIN="$FRONTEND_ORIGIN" \
    SESSION_SECRET="$SESSION_SECRET" \
    SESSION_COOKIE_SECURE=true \
    WEB_BASE_URL="$WEB_BASE_URL" \
    INITIAL_ADMIN_EMAIL="$INITIAL_ADMIN_EMAIL" \
    INITIAL_ADMIN_PASSWORD="$INITIAL_ADMIN_PASSWORD" \
    INITIAL_ADMIN_NAME="${INITIAL_ADMIN_NAME:-Admin}" \
    BOOTSTRAP_ADMIN="${BOOTSTRAP_ADMIN:-true}" \
    DATA_RETENTION_DAYS="${DATA_RETENTION_DAYS:-30}" \
    "$BACKEND_UVICORN" app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" \
    >"$BACKEND_LOG" 2>&1 < /dev/null &
  echo $! > "$BACKEND_PID_FILE"
}

start_frontend() {
  if [[ -f "$FRONTEND_PID_FILE" ]] && kill -0 "$(cat "$FRONTEND_PID_FILE")" >/dev/null 2>&1; then
    echo "Frontend already running"
    return
  fi

  echo "Building frontend"
  (cd "$FRONTEND_DIR" && VITE_APP_HOSTNAME="$APP_HOSTNAME" npm run build >"$FRONTEND_BUILD_LOG" 2>&1)

  echo "Starting frontend preview on ${FRONTEND_HOST}:${FRONTEND_PORT}"
  (
    cd "$FRONTEND_DIR"
    nohup VITE_APP_HOSTNAME="$APP_HOSTNAME" npm run preview -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" \
      >"$FRONTEND_LOG" 2>&1 < /dev/null &
    echo $! > "$FRONTEND_PID_FILE"
  )
}

start_backend
start_frontend

echo "Local web processes are running"
