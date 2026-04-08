# Bio Literature Digest Web

[中文说明 / README_zh](./README_zh.md)

Web console for `bio-literature-digest`. The producer writes normalized literature data into a shared database, and this project reads literature data from that shared database while keeping local auth/session operations.

Authentication mode is passwordless for internal use: users sign in with email only, and unknown emails are auto-provisioned as `member`.

Live instance-specific files live under `./bio-literature-config/`, split into deterministic `env/`, `data/`, `runtime/`, and `tunnel/` directories.

## Structure

- `backend/`: FastAPI API, SQLAlchemy models, shared-db consumers, Alembic bootstrap.
- `frontend/`: React + Vite single-page app.
- `deploy/`: Cloudflare Tunnel templates and deployment notes.
- `docs/`: deployment and architecture notes.
- `bio-literature-config/`: local-only instance root.
- `bio-literature-config/env/`: real env files and producer-side local config.
- `bio-literature-config/data/`: database, access traces, and review exports.
- `bio-literature-config/runtime/`: pid files and local process logs.
- `bio-literature-config/tunnel/`: Cloudflare Tunnel config and credentials.

## Quick Start

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 18002
```

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 18001
```

Tunnel-oriented local process startup:

```bash
./start.sh
```

This uses `./bio-literature-config/env/web/deploy.env.local` and starts a local Vite dev server with `/api` proxying:

- backend on the configured `BACKEND_HOST:BACKEND_PORT`
- frontend dev server on the configured `FRONTEND_HOST:FRONTEND_PORT`
- Cloudflare Tunnel when `ENABLE_TUNNEL=true` in the same config file

Default mode is no web-side scan/import. The producer sync step writes into the shared literature database directly.

## Syncing Web Accounts From Producer User Config

```bash
cd backend
. .venv/bin/activate
python sync_email_accounts.py
```

By default this reads `./bio-literature-config/env/producer/users.local.yaml` and syncs user identity fields (`email`, `name`, `role`, `group/user_group`, `is_active`). If `users.local.yaml` does not exist, it falls back to `email_config.local.yaml` and creates missing `member` users from enabled `to_emails`.

## Producer Integration

`bio-literature-digest` remains the only producer of daily digest content.

The integration contract is:

1. `bio-literature-digest/scripts/run_digest.py` generates artifacts and syncs normalized literature to the shared DB.
2. `bio-literature-digest/scripts/run_production_digest.py` archives the same daily run.
3. Web APIs read digest/paper data from the shared DB and write favorites/exports back to the shared DB.

Public access is intended to run through Cloudflare Tunnel on your configured public hostname, for example `https://app.example.com`.

## Harness

Canonical verification command:

```bash
python3 tools/run_harness.py
```

This runs:

- `python3 tools/resolve_instance_path.py`
- `backend/.venv/bin/python -m unittest discover -s app/tests`
- `npm run build` in `frontend/`
- `python3 tools/audit_open_source.py`

## Linux DO Declaration

Linux DO Declaration: this open-source baseline targets Linux operations (DO = Deployment Operator). All hostnames, paths, and account values in README/examples are placeholders and must be replaced before deployment.

## Harness

Canonical verification command:

```bash
python3 tools/run_harness.py
```

This runs:

- `python3 tools/resolve_instance_path.py`
- `backend/.venv/bin/python -m unittest discover -s app/tests`
- `npm run build` in `frontend/`
- `python3 tools/audit_open_source.py`

---

## Acknowledgments
Special thanks to the **[Linux.do](https://linux.do/)** community for your support and feedback.
