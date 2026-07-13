from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path

import yaml

from ..config import get_settings


def read_rules() -> tuple[Path, str, str]:
    path = Path(get_settings().producer_rules_path).resolve()
    content = path.read_text(encoding="utf-8")
    return path, content, hashlib.sha256(content.encode()).hexdigest()


def publish_rules(*, proposed_content: str, baseline_sha256: str, suggestion_id: str) -> str:
    path, current_content, current_hash = read_rules()
    if current_hash != baseline_sha256:
        raise ValueError("Rules changed since suggestion was created")
    parsed = yaml.safe_load(proposed_content)
    if not isinstance(parsed, dict):
        raise ValueError("Rules document must be a YAML mapping")

    settings = get_settings()
    backup_dir = Path(settings.producer_root).resolve() / "var" / "backups" / "rules"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    snapshot = backup_dir / f"{path.name}.{stamp}.{suggestion_id}.bak"
    snapshot.write_text(current_content, encoding="utf-8")

    staged = path.with_name(f".{path.name}.{suggestion_id}.staged")
    staged.write_text(proposed_content, encoding="utf-8")
    os.replace(staged, path)
    return str(snapshot)
