from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional

from .config import get_settings


def hash_password(password: str, salt: Optional[str] = None) -> str:
    resolved_salt = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), resolved_salt.encode("utf-8"), 120000)
    encoded = base64.b64encode(derived).decode("utf-8")
    return f"{resolved_salt}${encoded}"


def has_usable_password(password_hash: Optional[str]) -> bool:
    if not password_hash or password_hash == "passwordless":
        return False
    parts = password_hash.split("$", 1)
    return len(parts) == 2 and bool(parts[0]) and bool(parts[1])


def verify_password(password: str, password_hash: Optional[str]) -> bool:
    if not password or not has_usable_password(password_hash):
        return False
    assert password_hash is not None
    try:
        salt, _ = password_hash.split("$", 1)
    except ValueError:
        return False
    recalculated = hash_password(password, salt=salt)
    return hmac.compare_digest(recalculated, password_hash)


def create_session_token(*, ttl_seconds: int | None = None) -> tuple[str, str, datetime]:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(f"{settings.session_secret}:{token}".encode("utf-8")).hexdigest()
    lifetime = timedelta(seconds=ttl_seconds) if ttl_seconds is not None else timedelta(hours=settings.session_ttl_hours)
    expires_at = datetime.utcnow() + lifetime
    return token, token_hash, expires_at


def hash_session_token(token: str) -> str:
    settings = get_settings()
    return hashlib.sha256(f"{settings.session_secret}:{token}".encode("utf-8")).hexdigest()
