---
name: bio-literature-digest-web
description: Build and operate the web console for bio-literature-digest, including local-account auth, shared daily paper browsing, favorites, analytics, exports, and producer artifact import.
---

# Bio Literature Digest Web

## Overview

This project is the web consumer for `bio-literature-digest`.

- `backend/` provides FastAPI APIs, SQLAlchemy models, an importer CLI, and deployment-ready configuration.
- `frontend/` provides the authenticated React UI for daily papers, favorites, analytics, admin users, and exports.
- `deploy/` contains Cloudflare Tunnel templates and deployment notes for the configured public hostname.
- `bio-literature-config/` contains local-only secrets, Tunnel credentials, access traces, and review table exports.
- The current local process profile is frontend `127.0.0.1:8601`, backend `127.0.0.1:8602`, and ports in `8000-8200` are forbidden for startup scripts.

## Core Rules

- Treat `bio-literature-digest` as the producer of `digest.csv`, `digest.html`, `digest.xlsx`, and `run_metadata.json`.
- Do not reimplement the fetch/classify/translate pipeline in this project.
- Import producer outputs with `backend/import_digest_run.py --run-dir <path>`.
- Keep the shared daily paper pool global; per-user differences are favorites, exports, and personal analytics.
- Keep only two roles: `admin` and `member`.

## Commands

Backend:

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8602
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 8601
```

Importer:

```bash
cd backend
. .venv/bin/activate
python import_digest_run.py --run-dir /path/to/archived-run
```
