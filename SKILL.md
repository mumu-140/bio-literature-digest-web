---
name: bio-literature-digest-web
description: Build and operate the web console for bio-literature-digest, including local-account auth, shared daily paper browsing, favorites, analytics, and exports on shared data.
---

# Bio Literature Digest Web

## Overview

This project is the web consumer for `bio-literature-digest`.

- `backend/` provides FastAPI APIs, SQLAlchemy models, and deployment-ready configuration.
- `frontend/` provides the authenticated React UI for daily papers, favorites, analytics, admin users, and exports.
- `deploy/` contains Cloudflare Tunnel templates and deployment notes for the configured public hostname.
- `bio-literature-config/` is the local-only instance root.
- `bio-literature-config/env/` stores real env files.
- `bio-literature-config/data/` stores database and review/access data.
- `bio-literature-config/runtime/` stores pid files and logs.
- `bio-literature-config/tunnel/` stores Cloudflare Tunnel config and credentials.
- The producer root defaults to the sibling project `../bio-literature-digest`.
- The canonical operational entrypoints are `./start.sh` and `./stop.sh`. They read host, port, hostname, and public URL from `bio-literature-config/env/web/*.local`, and `ENABLE_TUNNEL` controls whether Cloudflare Tunnel is started.

## Core Rules

- Treat `bio-literature-digest` as the producer of `digest.csv`, `digest.html`, `digest.xlsx`, and `run_metadata.json`.
- Do not reimplement the fetch/classify/translate pipeline in this project.
- Read and write literature-related data through the shared database.
- Keep the shared daily paper pool global; per-user differences are favorites, exports, and personal analytics.
- Keep only two roles: `admin` and `member`.

## Commands

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

Harness:

```bash
python3 tools/run_harness.py
```
