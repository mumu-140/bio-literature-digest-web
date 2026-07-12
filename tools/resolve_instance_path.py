#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex

from instance_paths import get_instance_paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve the configured bio-literature-digest-web instance paths.")
    parser.add_argument("--shell", action="store_true", help="Print shell-safe KEY=VALUE lines for scripts")
    parser.add_argument("key", nargs="?", help="Single path key to print")
    args = parser.parse_args()

    paths = get_instance_paths()
    values = {
        "PROJECT_ROOT": str(paths.project_root),
        "WORKSPACE_ROOT": str(paths.workspace_root),
        "INSTANCE_ROOT": str(paths.instance_root),
        "WEB_ENV_DIR": str(paths.web_env_dir),
        "WEB_DATA_DIR": str(paths.web_data_dir),
        "WEB_RUNTIME_DIR": str(paths.web_runtime_dir),
        "WEB_TUNNEL_DIR": str(paths.web_tunnel_dir),
        "PRODUCER_ENV_DIR": str(paths.producer_env_dir),
        "PRODUCER_ROOT": str(paths.producer_root),
        "PRODUCER_ARCHIVE_DIR": str(paths.producer_archive_dir),
        "PRODUCER_DATABASE_FILE": str(paths.producer_database_file),
        "PRODUCER_EMAIL_CONFIG": str(paths.producer_email_config),
        "PRODUCER_USERS_CONFIG": str(paths.producer_users_config),
        "WEB_BACKEND_ENV_FILE": str(paths.backend_env_file),
        "WEB_DEPLOY_ENV_FILE": str(paths.deploy_env_file),
        "WEB_TUNNEL_CONFIG_FILE": str(paths.tunnel_config_file),
        "WEB_DATABASE_FILE": str(paths.database_file),
        "WEB_ACCESS_TRACE_DIR": str(paths.access_trace_dir),
        "WEB_REVIEW_EXPORT_DIR": str(paths.review_export_dir),
    }

    if args.shell:
        for key, value in values.items():
            print(f"{key}={shlex.quote(value)}")
        return 0
    if args.key:
        if args.key not in values:
            raise SystemExit(f"Unknown key: {args.key}")
        print(values[args.key])
        return 0
    for key, value in values.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
