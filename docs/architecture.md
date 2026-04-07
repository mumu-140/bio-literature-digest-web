# Architecture

## Producer / Consumer Split

- `bio-literature-digest` remains the producer of `digest.csv`, `digest.xlsx`, `digest.html`, and `run_metadata.json`.
- `bio-literature-digest-web` is the consumer. It imports producer artifacts, normalizes them into shared paper tables, and serves authenticated workflows.
- `bio-literature-digest-web/bio-literature-config/` is the live local-only instance root for the web project.
- `bio-literature-digest-web/bio-literature-config/paths.env` is the single source of truth for where env files, data, runtime logs, and Tunnel files live.

## Core Entities

- `users`: local login accounts with `admin` or `member` role.
- `sessions`: HttpOnly cookie-backed sessions.
- `digest_runs`: one imported producer run per digest date.
- `papers`: normalized global paper entities.
- `paper_daily_entries`: per-day membership in the shared digest pool.
- `favorites`: per-user paper references plus user-editable review metadata.
- `analytics_snapshots`, `analytics_nodes`, `analytics_edges`: persisted network graph materializations.
- `export_jobs`: generated downloads for metadata, DOI lists, and custom tables.
- `bio-literature-config/data/web/access-traces`: append-only per-user entry traces.
- `bio-literature-config/data/web/review-tables`: delayed review export output, including weighted aggregate sheets.

## Runtime Flow

1. Producer finishes a daily run.
2. Producer archives artifacts and calls `bio-literature-digest-web/backend/import_digest_run.py --run-dir <archive-dir>`.
3. Web backend imports rows into the shared paper pool.
4. Producer mail delivery reads the web `SESSION_SECRET` and embeds per-recipient passwordless links into the email.
5. Users log into the configured public hostname, browse daily papers, favorite records, run exports, and inspect analytics.
