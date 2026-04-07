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
mkdir -p bio-literature-config/web
cp bio-literature-config/web/deploy.env.local.example \
  bio-literature-config/web/deploy.env.local
```

Update:

- `APP_HOSTNAME`
- `DATABASE_URL`
- `SESSION_SECRET`
- `INITIAL_ADMIN_PASSWORD`

## 2. Start Local Web Processes

```bash
./start-amt-web.sh
```

This script:

- starts FastAPI on `${BACKEND_HOST}:${BACKEND_PORT}` with defaults `127.0.0.1:8602`
- builds the frontend and serves it on `${FRONTEND_HOST}:${FRONTEND_PORT}` with defaults `127.0.0.1:8601`
- reads public URL settings from `./bio-literature-config/web/deploy.env.local`
- forces secure cookies for the tunneled deployment
- rejects any backend/frontend port in the forbidden range `8000-8200`

Logs and pid files are written under `./.runtime/`.

Stop both processes with:

```bash
./stop-amt-web.sh
```

## 3. Cloudflare Tunnel

Copy the template config:

```bash
mkdir -p bio-literature-config/web/cloudflare-tunnel
cp deploy/cloudflare-tunnel/config.yml.example \
  bio-literature-config/web/cloudflare-tunnel/config.yml
```

Then update:

- `tunnel`: your Cloudflare Tunnel UUID
- `credentials-file`: the credential JSON file name in the same directory as `config.yml`
- `hostname`: your public hostname, for example `app.example.com`
- any backend/frontend port values here if you changed them in `deploy.env.local`

The ingress layout is:

- `/api/*` -> `127.0.0.1:8602`
- `/healthz` -> `127.0.0.1:8602`
- all other paths -> `127.0.0.1:8601`

Start the tunnel:

```bash
./start-amt-tunnel.sh
```

Stop it with:

```bash
./stop-amt-tunnel.sh
```

If you want `launchd` management, use `deploy/cloudflare-tunnel/com.acceptme.amt-bio-digest-tunnel.plist.example` as the base template.

## 4. Producer Bridge

`bio-literature-digest/scripts/run_production_digest.py` now supports:

```bash
python3 scripts/run_production_digest.py \
  --web-importer-python /path/to/bio-literature-digest-web/backend/.venv/bin/python3 \
  --web-backend-env-file /path/to/bio-literature-digest-web/bio-literature-config/web/backend.env.local \
  --web-base-url https://app.example.com
```

This keeps the existing mail workflow and archives intact while importing each successful daily run into the web database.

## 5. Direct Backend Development

If you run the backend directly instead of through `start-amt-web.sh`, it will load:

`bio-literature-config/web/backend.env.local`

That file is the local-development profile and is aligned to a frontend running on `http://127.0.0.1:8601`.
