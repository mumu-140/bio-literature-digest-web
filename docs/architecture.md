# Architecture

## Producer / Consumer Split

- `bio-literature-digest` remains the producer of `digest.csv`, `digest.xlsx`, `digest.html`, and `run_metadata.json`.
- `bio-literature-digest` also writes normalized literature data into a shared database.
- `bio-literature-digest-web` consumes the shared database directly for literature reads and literature-related writes (favorites, exports).
- `bio-literature-digest-web/bio-literature-config/` is the live local-only instance root for the web project.
- The web project resolves its runtime paths directly from the project root:
  - `bio-literature-config/env/web`
  - `bio-literature-config/data/web`
  - `bio-literature-config/runtime/web`
  - `bio-literature-config/tunnel/web`
- The producer side is resolved as the sibling project `../bio-literature-digest`, with archives under `../bio-literature-digest/archives/daily-digests`.

## Core Entities

- `users`: local login accounts with `admin` or `member` role.
- `sessions`: HttpOnly cookie-backed sessions.
- Local DB: `users`, `sessions`, and local operational records.
- Shared DB: `shared_literature_items`, `shared_digest_runs`, `shared_digest_memberships`, `shared_actor_favorites`, `shared_export_jobs`.
- `analytics_snapshots`, `analytics_nodes`, `analytics_edges`: persisted network graph materializations.
- `export_jobs`: generated downloads for metadata, DOI lists, and custom tables.
- `bio-literature-config/data/web/access-traces`: append-only per-user entry traces.
- `bio-literature-config/data/web/review-tables`: delayed review export output, including weighted aggregate sheets.

## Runtime Flow

1. Producer finishes a daily run.
2. Producer writes normalized literature and digest memberships into the shared database.
3. Web backend reads paper/digest lists from shared tables.
4. Web favorites and exports are persisted in shared tables.
5. Users log into the configured public hostname, browse daily papers, favorite records, run exports, and inspect analytics.
