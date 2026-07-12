---
name: bio-literature-digest-web
description: Build and operate the web consumer/workbench for bio-literature-digest, including local-account auth, imported literature browsing, favorites, exports, pushes, and low-frequency manual review on the web app's own data plane.
---

# Bio Literature Digest Web

## Overview

This project is the web consumer for `bio-literature-digest`.

- `backend/` provides FastAPI APIs, producer import integration, and local operational models.
- `frontend/` provides the authenticated React UI for daily papers, favorites, exports, pushes, and admin import controls.
- `deploy/cloudflare-tunnel/` contains the canonical public tunnel templates.
- `bio-literature-config/` is the local-only instance root.
- `bio-literature-config/env/` stores real env files.
- `bio-literature-config/data/` stores the local database, access traces, and review exports.
- `bio-literature-config/runtime/` stores pid files and logs.
- `bio-literature-config/tunnel/` stores real Cloudflare Tunnel config and credentials.
- The producer root defaults to the sibling project `../bio-literature-digest`.
- The canonical operational entrypoints are `./start.sh` and `./stop.sh`.

## Core Rules

- Treat `bio-literature-digest` as the only producer of literature content.
- Do not reimplement the producer fetch/classify/translate/archive pipeline in this project.
- Producer SQLite and producer archives are source inputs only.
- Keep the web UI reading only from the web app's own operational DB.
- Keep only two roles: `admin` and `member`.
- Do not restore analytics as a primary product surface.

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
