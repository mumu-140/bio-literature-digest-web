from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from .config import get_settings


def create_session_token() -> tuple[str, str, datetime]:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(f"{settings.session_secret}:{token}".encode("utf-8")).hexdigest()
    expires_at = datetime.utcnow() + timedelta(hours=settings.session_ttl_hours)
    return token, token_hash, expires_at


def hash_session_token(token: str) -> str:
    settings = get_settings()
    return hashlib.sha256(f"{settings.session_secret}:{token}".encode("utf-8")).hexdigest()
