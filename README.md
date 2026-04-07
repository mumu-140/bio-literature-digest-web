# Bio Literature Digest Web

[中文说明 / README_zh](./README_zh.md)

Web console for `bio-literature-digest`. The existing Python digest pipeline remains the producer; this project consumes `digest.csv` and `run_metadata.json`, stores shared daily papers, and exposes account management, favorites, analytics, and export workflows.

Live instance-specific files live under `./bio-literature-config/`, split into `env/`, `data/`, `runtime/`, and `tunnel/`.

## Structure

- `backend/`: FastAPI API, SQLAlchemy models, importer CLI, Alembic bootstrap.
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
uvicorn app.main:app --reload --host 127.0.0.1 --port 8602
```

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 8601
```

Tunnel-oriented local process startup:

```bash
./start-amt-web.sh
```

This uses `./bio-literature-config/env/web/deploy.env.local` and starts a local Vite dev server with `/api` proxying:

- backend on `127.0.0.1:8602`
- frontend dev server on `127.0.0.1:8601`

## Importing Existing Digest Runs

```bash
cd backend
. .venv/bin/activate
python import_digest_run.py --run-dir /path/to/daily-run
```

`bio-literature-digest/scripts/run_production_digest.py` now supports a post-run import bridge and web links in the email body.

## Syncing Web Accounts From Email Recipients

```bash
cd backend
. .venv/bin/activate
python sync_email_accounts.py
```

By default this reads the producer email config resolved through `./bio-literature-config/paths.env`, creates missing `member` users for enabled `to_emails`, and writes audit records for each created account.

## Producer Integration

`bio-literature-digest` remains the only producer of daily digest content.

The integration contract is:

1. `bio-literature-digest/scripts/run_digest.py` generates `digest.csv`, `digest.xlsx`, `digest.html`, and `run_metadata.json`.
2. `bio-literature-digest/scripts/run_production_digest.py` archives the same daily run and then calls `bio-literature-digest-web/backend/import_digest_run.py`.
3. The importer writes the shared daily paper pool into the web database.
4. `bio-literature-digest/scripts/send_email.py` resolves the web instance root through `BIO_DIGEST_WEB_ROOT` or the default sibling path, then reads `bio-literature-digest-web/bio-literature-config/env/web/backend.env.local` to reuse the web `SESSION_SECRET`.

Public access is intended to run through Cloudflare Tunnel on your configured public hostname, for example `https://app.example.com`.
---

## Acknowledgments
Special thanks to the **[Linux.do](https://linux.do/)** community for your support and feedback.
