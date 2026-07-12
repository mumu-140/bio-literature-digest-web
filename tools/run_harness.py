#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
BACKEND_PYTHON = BACKEND_ROOT / ".venv" / "bin" / "python"
PATH_RESOLVER = PROJECT_ROOT / "tools" / "resolve_instance_path.py"
AUDIT_SCRIPT = PROJECT_ROOT / "tools" / "audit_open_source.py"


def run_step(label: str, command: list[str], *, cwd: Path) -> int:
    print(f"[harness] {label}: {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=cwd)
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the canonical bio-literature-digest-web harness.")
    parser.add_argument("--skip-paths", action="store_true", help="Skip instance path resolution check")
    parser.add_argument("--skip-audit", action="store_true", help="Skip repository layout and sanitization audit")
    parser.add_argument("--skip-backend", action="store_true", help="Skip backend unittest discovery")
    parser.add_argument("--skip-frontend", action="store_true", help="Skip frontend production build")
    args = parser.parse_args()

    if not args.skip_paths:
        path_status = run_step(
            "instance-paths",
            [sys.executable, str(PATH_RESOLVER)],
            cwd=PROJECT_ROOT,
        )
        if path_status != 0:
            return path_status

    if not args.skip_backend:
        backend_python = str(BACKEND_PYTHON) if BACKEND_PYTHON.exists() else sys.executable
        backend_status = run_step(
            "backend-tests",
            [backend_python, "-m", "unittest", "discover", "-s", "app/tests"],
            cwd=BACKEND_ROOT,
        )
        if backend_status != 0:
            return backend_status

    if not args.skip_frontend:
        frontend_status = run_step(
            "frontend-build",
            ["npm", "run", "build"],
            cwd=PROJECT_ROOT / "frontend",
        )
        if frontend_status != 0:
            return frontend_status

    if not args.skip_audit:
        audit_status = run_step(
            "open-source-audit",
            [sys.executable, str(AUDIT_SCRIPT)],
            cwd=PROJECT_ROOT,
        )
        if audit_status != 0:
            return audit_status

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
