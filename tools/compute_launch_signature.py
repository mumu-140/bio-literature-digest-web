#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SERVICE_PATHS = {
    "backend": [
        "backend/app",
        "backend/alembic",
        "backend/requirements.txt",
        "bio-literature-config/env/web/backend.env.local",
        "start.sh",
        "stop.sh",
    ],
    "frontend": [
        "frontend/src",
        "frontend/package.json",
        "frontend/package-lock.json",
        "frontend/tsconfig.json",
        "frontend/tsconfig.app.json",
        "frontend/vite.config.ts",
        "bio-literature-config/env/web/deploy.env.local",
        "start.sh",
        "stop.sh",
    ],
    "archive-sync": [
        "backend/app",
        "backend/alembic",
        "backend/sync_archives.py",
        "backend/requirements.txt",
        "bio-literature-config/env/web/backend.env.local",
        "bio-literature-config/env/web/deploy.env.local",
        "start.sh",
        "stop.sh",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute a service launch signature from code/config inputs.")
    parser.add_argument("--root", required=True, help="Project root")
    parser.add_argument("--service", choices=sorted(SERVICE_PATHS), required=True)
    parser.add_argument("--salt", action="append", default=[], help="Extra key=value salt values")
    return parser.parse_args()


def iter_files(root: Path, relative_targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for target in relative_targets:
        path = (root / target).resolve()
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
            continue
        files.extend(sorted(item for item in path.rglob("*") if item.is_file()))
    return sorted(files, key=lambda item: str(item.relative_to(root)))


def compute_signature(root: Path, service: str, salts: list[str]) -> str:
    digest = hashlib.sha256()
    digest.update(f"service:{service}\n".encode("utf-8"))
    for salt in salts:
        digest.update(f"salt:{salt}\n".encode("utf-8"))

    for path in iter_files(root, SERVICE_PATHS[service]):
        relative = str(path.relative_to(root))
        digest.update(f"path:{relative}\n".encode("utf-8"))
        digest.update(path.read_bytes())
        digest.update(b"\n")
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    print(compute_signature(root, args.service, args.salt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
