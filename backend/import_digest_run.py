#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app import database
from app.migrations import run_runtime_migrations
from app.services.importer import import_digest_run, iter_run_directories


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a bio-literature-digest run directory into the web database.")
    parser.add_argument("--run-dir", action="append", default=[], help="Run directory containing digest.csv and run_metadata.json")
    parser.add_argument("--archives-root", help="Import every valid run directory under this root")
    parser.add_argument("--days", type=int, help="Only import the most recent N run directories from --archives-root")
    parser.add_argument("--database-url", help="Override database URL")
    args = parser.parse_args()
    if not args.run_dir and not args.archives_root:
        parser.error("Either --run-dir or --archives-root is required")

    database.configure_database(args.database_url)
    run_runtime_migrations(database.engine)
    database.Base.metadata.create_all(bind=database.engine)
    run_dirs = [Path(path) for path in args.run_dir]
    if args.archives_root:
        discovered = list(iter_run_directories(Path(args.archives_root)))
        if args.days:
            discovered = discovered[-args.days :]
        run_dirs.extend(discovered)
    deduped_run_dirs: list[Path] = []
    seen: set[Path] = set()
    for run_dir in sorted(path.resolve() for path in run_dirs):
        if run_dir not in seen:
            deduped_run_dirs.append(run_dir)
            seen.add(run_dir)
    with database.SessionLocal() as db:
        for run_dir in deduped_run_dirs:
            digest_run, imported = import_digest_run(db, run_dir)
            print(f"Imported digest run {digest_run.id} for {digest_run.digest_date} with {imported} papers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
