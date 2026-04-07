from __future__ import annotations

import argparse
import json

from app import database
from app.migrations import run_runtime_migrations
from app.services.favorite_review_exports import export_favorite_review_tables


def main() -> int:
    parser = argparse.ArgumentParser(description="Export per-user and weighted favorite review tables.")
    parser.parse_args()
    database.configure_database()
    run_runtime_migrations(database.engine)
    database.Base.metadata.create_all(bind=database.engine)
    with database.SessionLocal() as db:
        manifest = export_favorite_review_tables(db)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
