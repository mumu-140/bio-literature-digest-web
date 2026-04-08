# Deployment

## 1. Prepare Environment

Backend venv:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Frontend dependencies:

```bash
cd frontend
npm install
```

Deploy env:

```bash
mkdir -p bio-literature-config/env/web
cp bio-literature-config/env/web/deploy.env.local.example \
  bio-literature-config/env/web/deploy.env.local
```

Update:

- `APP_HOSTNAME`
- `DATABASE_URL`
- `SESSION_SECRET`
- `INITIAL_ADMIN_EMAIL`

Login is passwordless for internal use. The web app signs in by email, and unknown emails are auto-created as `member`.

## 2. Start Local Web Processes

```bash
./start.sh
```

This script:

- starts FastAPI on `${BACKEND_HOST}:${BACKEND_PORT}`
- starts the Vite dev server on `${FRONTEND_HOST}:${FRONTEND_PORT}`
- starts Cloudflare Tunnel when `ENABLE_TUNNEL=true`
- proxies `/api` from the frontend dev server to the backend
- reads public URL settings from `./bio-literature-config/env/web/deploy.env.local`
- uses `LOCAL_FRONTEND_ORIGIN` for local cookies and honors `SESSION_COOKIE_SECURE`
- rejects backend/frontend ports inside `${RESERVED_PORT_RANGE}` when that variable is set

Logs and pid files are written under `./bio-literature-config/runtime/web/`.

Stop all managed processes with:

```bash
./stop.sh
```

## 3. Cloudflare Tunnel

Copy the template config:

```bash
mkdir -p bio-literature-config/tunnel/web
cp deploy/cloudflare-tunnel/config.yml.example \
  bio-literature-config/tunnel/web/config.yml
```

Then update:

- `tunnel`: your Cloudflare Tunnel UUID
- `credentials-file`: the credential JSON file name in the same directory as `config.yml`
- `hostname`: your public hostname, for example `app.example.com`
- each backend/frontend service target so it matches `env/web/deploy.env.local`

The ingress layout is:

- `/api/*` -> `${BACKEND_HOST}:${BACKEND_PORT}`
- `/healthz` -> `${BACKEND_HOST}:${BACKEND_PORT}`
- all other paths -> `${FRONTEND_HOST}:${FRONTEND_PORT}`

Set `ENABLE_TUNNEL=false` in `env/web/deploy.env.local` if you want to start only backend and frontend without the public tunnel.

If you want `launchd` management, use `deploy/cloudflare-tunnel/com.example.bio-digest-web-tunnel.plist.example` as the base template.

## 4. Producer Bridge

`bio-literature-digest/scripts/run_production_digest.py` now supports:

```bash
python3 scripts/run_production_digest.py \
  --web-base-url https://app.example.com \
  --shared-db-url sqlite:////absolute/path/to/bio_literature_shared.db
```

This keeps the existing mail workflow and archives intact while ensuring the producer-side shared database sync is executed.

## 5. Direct Backend Development

If you run the backend directly instead of through `start.sh`, it will load:

`bio-literature-config/env/web/backend.env.local`

That file is the local-development profile and is aligned to the frontend origin declared inside `env/web/backend.env.local`.

## 6. Harness

Run the canonical harness after changing path resolution, shared-db behavior, or deployment scripts:

```bash
python3 tools/run_harness.py
```
