# Bio Literature Digest Web

[中文说明 / README_zh](./README_zh.md)

`bio-literature-digest-web` is an independent consumer/workbench for `bio-literature-digest`.

- `bio-literature-digest` remains the only producer of literature content.
- Producer SQLite and producer archives are read-only source inputs.
- The web UI reads only from the web app's own operational database.
- The product surface is focused on reading, favorites, exports, pushes, and low-frequency manual review input.

## Supported Structure

- `backend/`: FastAPI API, importer, local operational models, tests.
- `frontend/`: React + Vite UI.
- `deploy/cloudflare-tunnel/`: canonical public tunnel templates.
- `docs/`: architecture and deployment notes.
- `bio-literature-config/`: local-only instance root.
- `bio-literature-config/env/`: real env files and producer-side local config.
- `bio-literature-config/data/`: local database, access traces, review exports.
- `bio-literature-config/runtime/`: pid files and local logs.
- `bio-literature-config/tunnel/`: real Cloudflare Tunnel config and credentials.

## Runtime Model

1. The producer finishes a run and writes producer SQLite rows.
2. This web app imports the latest usable completed run into its local operational DB at startup, or via admin manual import/re-import.
3. Archives and export artifacts are validation/fallback only; they do not block SQLite-based import.
4. The UI reads local imported content, local favorites, local manual review, local pushes, and local export jobs.

There is no analytics surface in the supported product.

## Quick Start

Backend:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 18002
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 18001
```

Managed local-process workflow:

```bash
./start.sh
./stop.sh
```

`start.sh` reads `bio-literature-config/env/web/deploy.env.local`, starts the backend, starts the frontend dev server, and optionally starts Cloudflare Tunnel when `ENABLE_TUNNEL=true`.

## Producer Integration

This project assumes the producer lives at the sibling path `../bio-literature-digest` unless overridden by env.

Read-only producer inputs:

- producer SQLite database
- producer run archives
- producer users config for account sync
- producer rules/template files for manual review export formatting

The supported import path is:

- startup import check
- admin import check
- admin import specific run
- admin force re-import specific run

## Manual Review Export

Manual review export reads only from the web operational DB and renders through the producer formatter using `daily_review_schema`.

Supported naming:

- per-user: `<producer_uid>-data.xlsx`
- fallback: `webuser-<id>-data.xlsx`
- aggregate: `aggregate-data.xlsx`

Matching `.csv` and `.html` sidecars use the same stem.

CLI entrypoint:

```bash
cd backend
. .venv/bin/activate
python export_favorite_review_tables.py
```

## Cloudflare Tunnel

Use the single canonical template:

```bash
cp deploy/cloudflare-tunnel/config.yml.example \
  bio-literature-config/tunnel/web/config.yml
```

Do not commit the real `bio-literature-config/tunnel/web/config.yml` or any credential JSON files.

## Validation

Canonical verification command:

```bash
python3 tools/run_harness.py
```

This runs:

- `python3 tools/resolve_instance_path.py`
- `backend/.venv/bin/python -m unittest discover -s app/tests`
- `npm run build` in `frontend/`
- `python3 tools/audit_open_source.py`

## Acknowledgments
Special thanks to the **[Linux.do](https://linux.do/)** community for your support and feedback.
