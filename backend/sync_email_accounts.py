#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from app import database
from app.migrations import run_runtime_migrations
from app.services.user_sync import sync_users_from_email_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = PROJECT_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from instance_paths import get_instance_paths

INSTANCE_PATHS = get_instance_paths(PROJECT_ROOT)
DEFAULT_EMAIL_CONFIG = INSTANCE_PATHS.producer_email_config


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync web users from bio-literature-digest email recipients.")
    parser.add_argument("--email-config", default=str(DEFAULT_EMAIL_CONFIG), help="Producer email_config.local.yaml path")
    parser.add_argument("--database-url", help="Override database URL")
    args = parser.parse_args()

    database.configure_database(args.database_url)
    run_runtime_migrations(database.engine)
    database.Base.metadata.create_all(bind=database.engine)

    config_path = Path(args.email_config).resolve()
    if not config_path.exists():
        raise SystemExit(f"Email config not found: {config_path}")

    with database.SessionLocal() as db:
        result = sync_users_from_email_config(db, config_path=config_path)

    print(f"Recipients discovered: {len(result.recipients)}")
    print(f"Users created: {len(result.created)}")
    for user in result.created:
        print(f"CREATED {user.id} {user.email} {user.name} {user.role}")
    print(f"Users already existed: {len(result.existing)}")
    for user in result.existing:
        print(f"EXISTING {user.id} {user.email} {user.name} {user.role}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
