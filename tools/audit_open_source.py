#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]

IGNORED_PARTS = {
    ".venv",
    "node_modules",
    "dist",
    ".pytest_cache",
    "__pycache__",
}

IGNORED_FILENAMES = {
    ".DS_Store",
}

IGNORED_PREFIXES = [
    Path("bio-literature-config/data"),
    Path("bio-literature-config/runtime"),
    Path("bio-literature-config/env"),
    Path("bio-literature-config/tunnel"),
]

BANNED_PATTERNS = {
    r"/Users/": "absolute macOS home path",
    r"/opt/homebrew/bin/": "package-manager-specific binary path",
    r"accept\.me": "project-specific public hostname",
    r"popgod\.us\.ci": "project-specific public hostname",
    r"admin@popgod\.us\.ci": "project-specific admin identity",
}

LEGACY_FILES = [
    Path("backend/Dockerfile"),
    Path("frontend/Dockerfile"),
    Path("deploy/docker-compose.yml"),
    Path("deploy/Caddyfile"),
    Path("deploy/.env.example"),
    Path("backend/.env.example"),
]

REQUIRED_DIRECTORIES = [
    Path("backend"),
    Path("frontend"),
    Path("tools"),
    Path("docs"),
    Path("deploy/cloudflare-tunnel"),
    Path("bio-literature-config/env"),
    Path("bio-literature-config/data"),
    Path("bio-literature-config/runtime"),
    Path("bio-literature-config/tunnel"),
]

REQUIRED_FILES = [
    Path("start.sh"),
    Path("stop.sh"),
    Path("tools/run_harness.py"),
    Path("tools/audit_open_source.py"),
    Path("tools/resolve_instance_path.py"),
    Path("bio-literature-config/env/web/backend.env.local.example"),
    Path("bio-literature-config/env/web/deploy.env.local.example"),
    Path("deploy/cloudflare-tunnel/config.yml.example"),
    Path("deploy/cloudflare-tunnel/com.example.bio-digest-web-tunnel.plist.example"),
]


def is_public_template(path: Path) -> bool:
    name = path.name
    return (
        name.endswith(".example")
        or ".example." in name
        or name.endswith(".sample")
        or ".sample." in name
    )


def should_skip(path: Path) -> bool:
    rel = path.relative_to(PROJECT_ROOT)
    if any(part in IGNORED_PARTS for part in rel.parts):
        return True
    for prefix in IGNORED_PREFIXES:
        if rel == prefix or prefix in rel.parents:
            return not is_public_template(rel)
    return False


def scan_content() -> list[str]:
    problems: list[str] = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file() or should_skip(path):
            continue
        if path.name in IGNORED_FILENAMES:
            continue
        if path == Path(__file__).resolve():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern, label in BANNED_PATTERNS.items():
            if re.search(pattern, text):
                problems.append(f"{label} in {path.relative_to(PROJECT_ROOT)}")
    return problems


def scan_layout() -> list[str]:
    problems: list[str] = []
    for rel_path in LEGACY_FILES:
        if (PROJECT_ROOT / rel_path).exists():
            problems.append(f"unsupported legacy deployment artifact present: {rel_path}")
    for required in (PROJECT_ROOT / path for path in REQUIRED_DIRECTORIES):
        if not required.exists():
            problems.append(f"missing required directory: {required.relative_to(PROJECT_ROOT)}")
    for required in (PROJECT_ROOT / path for path in REQUIRED_FILES):
        if not required.exists():
            problems.append(f"missing required file: {required.relative_to(PROJECT_ROOT)}")
    return problems


def main() -> int:
    problems = scan_layout() + scan_content()
    if problems:
        for problem in problems:
            print(f"[audit] {problem}")
        return 1
    print("[audit] repository layout and sanitization checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
