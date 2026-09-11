from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Callable

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..deps import get_db
from ..models import ApiClient


def hash_api_key(token: str) -> str:
    settings = get_settings()
    return hashlib.sha256(f"{settings.session_secret}:{token}".encode()).hexdigest()


def bootstrap_api_client(db: Session) -> None:
    settings = get_settings()
    token = settings.literature_api_bootstrap_token.strip()
    if not token:
        return
    client = db.scalar(select(ApiClient).where(ApiClient.name == settings.literature_api_client_name))
    if client is None:
        client = ApiClient(name=settings.literature_api_client_name, key_hash=hash_api_key(token))
        db.add(client)
    client.key_hash = hash_api_key(token)
    client.scopes_json = [scope.strip() for scope in settings.literature_api_scopes.split(",") if scope.strip()]
    client.is_active = True
    db.commit()


def get_api_client(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> ApiClient:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer API key required")
    token = authorization.removeprefix("Bearer ").strip()
    client = db.scalar(select(ApiClient).where(ApiClient.key_hash == hash_api_key(token)))
    if client is None or not client.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    client.last_used_at = datetime.utcnow()
    db.flush()
    return client


def require_api_scopes(*required: str) -> Callable:
    def dependency(client: ApiClient = Depends(get_api_client)) -> ApiClient:
        missing = set(required) - set(client.scopes_json or [])
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing API scopes: {', '.join(sorted(missing))}",
            )
        return client
    return dependency
