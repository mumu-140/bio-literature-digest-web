from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import re
import shutil
import tempfile

import yaml


UID_PATTERN = re.compile(r"^UDI-(\d+)$")


class SubscriptionEmailExistsError(ValueError):
    """Raised when the subscription email already exists."""


@dataclass(frozen=True)
class SubscriptionEmailResult:
    uid: str
    email: str
    name: str
    user_group: str
    smtp_profile: str
    backup_path: str


def add_subscription_email(
    config_path: Path,
    *,
    email: str,
    name: str,
    user_group: str,
    smtp_profile: str = "qq_mail",
) -> SubscriptionEmailResult:
    """Append one enabled digest recipient with a locked, backed-up atomic write."""
    normalized_email = email.strip().lower()
    resolved_name = name.strip() or normalized_email.split("@", 1)[0]
    config_path = config_path.resolve()
    lock_path = config_path.with_suffix(f"{config_path.suffix}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        payload = _read_payload(config_path)
        users = payload.setdefault("users", [])
        if not isinstance(users, list):
            raise ValueError("users.yaml must contain a users list")
        if any(str(user.get("email", "")).strip().lower() == normalized_email for user in users if isinstance(user, dict)):
            raise SubscriptionEmailExistsError(f"订阅邮箱已存在：{normalized_email}")

        backup_path = _backup_config(config_path)
        uid = _next_uid(users)
        users.append(
            {
                "uid": uid,
                "email": normalized_email,
                "name": resolved_name,
                "role": "member",
                "group": user_group,
                "is_active": True,
                "receives_digest": True,
                "smtp_profile": smtp_profile,
            }
        )
        _atomic_write_yaml(config_path, payload)

    return SubscriptionEmailResult(
        uid=uid,
        email=normalized_email,
        name=resolved_name,
        user_group=user_group,
        smtp_profile=smtp_profile,
        backup_path=str(backup_path),
    )


def _read_payload(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Producer users config not found: {config_path}")
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("users.yaml must contain a mapping")
    return payload


def _next_uid(users: list) -> str:
    highest = 0
    for user in users:
        if not isinstance(user, dict):
            continue
        match = UID_PATTERN.match(str(user.get("uid", "")).strip())
        if match:
            highest = max(highest, int(match.group(1)))
    return f"UDI-{highest + 1:04d}"


def _backup_config(config_path: Path) -> Path:
    project_root = config_path.parents[2]
    backup_dir = project_root / "var" / "backups" / "users"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"users.yaml.before-subscription-{timestamp}"
    shutil.copy2(config_path, backup_path)
    return backup_path


def _atomic_write_yaml(config_path: Path, payload: dict) -> None:
    rendered = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    descriptor, temp_name = tempfile.mkstemp(prefix=".users.", suffix=".yaml", dir=config_path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, config_path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
