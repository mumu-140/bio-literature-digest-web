# Architecture

## Producer / Consumer Boundary

- `bio-literature-digest` is the only producer of literature content.
- Producer SQLite and producer archives are source inputs only.
- `bio-literature-digest-web` imports producer runs into its own local operational database.
- The web UI never reads producer SQLite or producer archives directly.

## Local Operational Data Plane

Primary web-side tables:

- `users`
- `sessions`
- `imported_literature_items`
- `imported_digest_runs`
- `imported_digest_memberships`
- `producer_import_ledger`
- `user_literature_favorites`
- `user_manual_reviews`
- `user_export_jobs_v2`
- `literature_pushes_v2`
- `action_logs`

These tables are the supported runtime surface for reading, favorites, manual review, exports, pushes, and import auditability.

## Canonical Identity

- Literature item key: producer `papers.unique_key`
- Digest membership key: `(digest_date, list_type, literature_item_key)`
- Favorite key: `(user_id, literature_item_key)`
- Manual review key: `(user_id, literature_item_key)`

Missing `unique_key` rows are skipped and logged. Re-import replaces memberships for the target digest date but preserves favorites and manual review attached to the same literature key.

## Import Flow

1. Read producer SQLite runs and paper records.
2. Choose the latest usable run per digest date by `updated_at_utc`.
3. Import immediately from SQLite when the run is usable.
4. Validate archive/export artifacts when present without blocking import.
5. Upsert local literature items and replace local memberships for that digest date.
6. Record the result in `producer_import_ledger` and `action_logs`.

Startup keeps one import check. Admins can also check, import, or force re-import manually.

## Manual Review Export

Manual review export reads only:

- local imported literature metadata
- local digest memberships
- local manual review rows

Output is rendered through the producer export formatter with `daily_review_schema`.

Naming:

- per-user: `<uid>-data.xlsx`
- fallback: `webuser-<id>-data.xlsx`
- aggregate: `aggregate-data.xlsx`

Matching `.csv` and `.html` sidecars use the same stem.

## Historical Alembic Files

- `backend/alembic/versions/0001_initial.py` and `backend/alembic/versions/0002_paper_pushes.py` are retained as historical migration snapshots.
- They still mention removed analytics and legacy local-content tables.
- They are not the current architecture source of truth.
- For the supported runtime architecture, use `backend/app/models.py`, `backend/app/migrations.py`, and `backend/app/integrations/producer_import/`.
