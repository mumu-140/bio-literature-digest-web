from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional

from .config import get_settings


def hash_password(password: str, salt: Optional[str] = None) -> str:
    resolved_salt = salt or secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), resolved_salt.encode("utf-8"), 120000)
    encoded = base64.b64encode(derived).decode("utf-8")
    return f"{resolved_salt}${encoded}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, encoded = password_hash.split("$", 1)
    except ValueError:
        return False
    recalculated = hash_password(password, salt=salt)
    return hmac.compare_digest(recalculated, password_hash)


def create_session_token() -> tuple[str, str, datetime]:
    settings = get_settings()
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(f"{settings.session_secret}:{token}".encode("utf-8")).hexdigest()
    expires_at = datetime.utcnow() + timedelta(hours=settings.session_ttl_hours)
    return token, token_hash, expires_at


def hash_session_token(token: str) -> str:
    settings = get_settings()
    return hashlib.sha256(f"{settings.session_secret}:{token}".encode("utf-8")).hexdigest()


def _sign_token_payload(payload_bytes: bytes) -> str:
    settings = get_settings()
    signature = hmac.new(settings.session_secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")


def _encode_token_payload(payload: dict[str, str | int]) -> str:
    payload_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
    signature = _sign_token_payload(payload_bytes)
    return f"{encoded_payload}.{signature}"


def _decode_token_payload(token: str) -> dict[str, str | int] | None:
    try:
        encoded_payload, signature = token.split(".", 1)
        payload_bytes = base64.urlsafe_b64decode(encoded_payload + "=" * (-len(encoded_payload) % 4))
    except Exception:
        return None
    expected_signature = _sign_token_payload(payload_bytes)
    if not hmac.compare_digest(signature, expected_signature):
        return None
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def create_email_login_token(email: str) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.utcnow() + timedelta(hours=settings.email_login_ttl_hours)
    token = _encode_token_payload(
        {
            "sub": email.strip().lower(),
            "kind": "email-login",
            "exp": int(expires_at.timestamp()),
        }
    )
    return token, expires_at


def verify_email_login_token(token: str, email: str) -> bool:
    payload = _decode_token_payload(token)
    if payload is None:
        return False
    try:
        exp = int(payload.get("exp", 0))
    except (TypeError, ValueError):
        return False
    if payload.get("kind") != "email-login":
        return False
    if str(payload.get("sub", "")).strip().lower() != email.strip().lower():
        return False
    return exp >= int(datetime.utcnow().timestamp())
