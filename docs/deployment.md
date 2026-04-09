# Deployment

## 1. Prepare Local Environment

Backend:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Frontend:

```bash
cd frontend
npm install
```

Prepare local env files:

```bash
mkdir -p bio-literature-config/env/web
cp bio-literature-config/env/web/backend.env.local.example \
  bio-literature-config/env/web/backend.env.local
cp bio-literature-config/env/web/deploy.env.local.example \
  bio-literature-config/env/web/deploy.env.local
```

Minimum web settings:

- `DATABASE_URL`
- `SESSION_SECRET`
- `INITIAL_ADMIN_EMAIL`
- `WEB_BASE_URL`

## 2. Producer Inputs

This project expects read-only producer inputs:

- producer SQLite database
- producer archives
- producer users config
- producer review rules/template files

Defaults resolve to the sibling project `../bio-literature-digest`, but paths can be overridden by env.

## 3. Start Local Processes

```bash
./start.sh
```

This script:

- starts FastAPI on `${BACKEND_HOST}:${BACKEND_PORT}`
- starts the Vite dev server on `${FRONTEND_HOST}:${FRONTEND_PORT}`
- runs one startup producer import check
- starts Cloudflare Tunnel when `ENABLE_TUNNEL=true`
- writes pid files and logs under `bio-literature-config/runtime/web/`

Stop with:

```bash
./stop.sh
```

## 4. Cloudflare Tunnel

Use the single canonical template:

```bash
mkdir -p bio-literature-config/tunnel/web
cp deploy/cloudflare-tunnel/config.yml.example \
  bio-literature-config/tunnel/web/config.yml
```

Then update:

- `tunnel`
- `credentials-file`
- `hostname`
- backend/frontend service targets so they match `env/web/deploy.env.local`

Optional `launchd` template:

- `deploy/cloudflare-tunnel/com.example.bio-digest-web-tunnel.plist.example`

## 5. Import Operations

The supported import controls are:

- startup import check
- admin import check
- admin import one run
- admin force re-import one run

There is no supported periodic polling window.

## 6. Review Export

Manual review export stays local-plane only:

```bash
cd backend
. .venv/bin/activate
python export_favorite_review_tables.py
```

It renders the provided review table format through the producer formatter and writes outputs under `bio-literature-config/data/web/review-tables/`.

## 7. Validation

```bash
python3 tools/run_harness.py
```
