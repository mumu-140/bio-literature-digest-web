from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import secrets
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import User
from ..security import hash_password
from .audit import record_action


@dataclass
class SyncedUser:
    id: int
    email: str
    name: str
    role: str


@dataclass
class UserSyncResult:
    recipients: list[str]
    created: list[SyncedUser]
    existing: list[SyncedUser]


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _parse_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _collect_recipients_from_yaml_mapping(payload: dict[str, Any]) -> list[str]:
    profiles = payload.get("smtp_profiles")
    if not isinstance(profiles, dict):
        return []
    recipients: list[str] = []
    for profile in profiles.values():
        if not isinstance(profile, dict):
            continue
        if not _parse_bool(profile.get("enabled"), default=True):
            continue
        values = profile.get("to_emails") or []
        if not isinstance(values, list):
            continue
        for value in values:
            if value:
                recipients.append(str(value).strip().lower())
    return _dedupe(recipients)


def _collect_recipients_from_text(raw_text: str) -> list[str]:
    in_smtp_profiles = False
    current_profile: dict[str, Any] | None = None
    current_profile_indent = 0
    collecting_to_emails = False
    profiles: list[dict[str, Any]] = []

    for raw_line in raw_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 0:
            collecting_to_emails = False
            current_profile = None
            if stripped == "smtp_profiles:":
                in_smtp_profiles = True
                continue
            if in_smtp_profiles:
                break
            continue
        if not in_smtp_profiles:
            continue
        if indent == 2 and stripped.endswith(":"):
            current_profile = {"enabled": True, "to_emails": []}
            current_profile_indent = indent
            profiles.append(current_profile)
            collecting_to_emails = False
            continue
        if current_profile is None:
            continue
        if indent <= current_profile_indent:
            current_profile = None
            collecting_to_emails = False
            continue
        if indent == 4 and stripped.startswith("enabled:"):
            current_profile["enabled"] = _parse_bool(_strip_quotes(stripped.split(":", 1)[1]))
            collecting_to_emails = False
            continue
        if indent == 4 and stripped == "to_emails:":
            collecting_to_emails = True
            continue
        if indent == 4:
            collecting_to_emails = False
            continue
        if collecting_to_emails and indent >= 6 and stripped.startswith("- "):
            current_profile["to_emails"].append(_strip_quotes(stripped[2:]).strip().lower())

    recipients: list[str] = []
    for profile in profiles:
        if not _parse_bool(profile.get("enabled"), default=True):
            continue
        recipients.extend(profile.get("to_emails", []))
    return _dedupe(recipients)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def read_recipient_emails(config_path: Path) -> list[str]:
    raw_text = config_path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        payload = yaml.safe_load(raw_text) or {}
        if isinstance(payload, dict):
            return _collect_recipients_from_yaml_mapping(payload)
    except Exception:
        pass
    return _collect_recipients_from_text(raw_text)


def derive_display_name(email: str) -> str:
    local_part = email.split("@", 1)[0].strip()
    return local_part or email


def sync_users_from_email_config(
    db: Session,
    *,
    config_path: Path,
    actor_user_id: int | None = None,
    default_role: str = "member",
) -> UserSyncResult:
    recipients = read_recipient_emails(config_path)
    created: list[SyncedUser] = []
    existing: list[SyncedUser] = []

    for email in recipients:
        user = db.scalar(select(User).where(User.email == email))
        if user is not None:
            existing.append(SyncedUser(id=user.id, email=user.email, name=user.name, role=user.role))
            continue
        user = User(
            email=email,
            name=derive_display_name(email),
            password_hash=hash_password(secrets.token_urlsafe(24)),
            role=default_role,
            is_active=True,
            must_change_password=True,
        )
        db.add(user)
        db.flush()
        record_action(
            db,
            action_type="sync_email_recipient_create_user",
            actor_user_id=actor_user_id,
            target_user_id=user.id,
            entity_type="user",
            entity_id=user.id,
            detail={"email": user.email, "role": user.role, "config_path": str(config_path)},
        )
        created.append(SyncedUser(id=user.id, email=user.email, name=user.name, role=user.role))

    db.commit()
    return UserSyncResult(recipients=recipients, created=created, existing=existing)
