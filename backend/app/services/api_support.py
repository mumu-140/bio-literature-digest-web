from __future__ import annotations

import hashlib
import json
import uuid

from fastapi import HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ApiAuditEvent, ApiClient, ApiIdempotencyRecord


def request_id(request: Request) -> str:
    existing = getattr(request.state, "request_id", "")
    if existing:
        return existing
    value = request.headers.get("X-Request-ID", "").strip() or str(uuid.uuid4())
    request.state.request_id = value
    return value


def record_api_audit(
    db: Session,
    *,
    request: Request,
    client: ApiClient | None,
    action: str,
    entity_type: str = "",
    entity_key: str = "",
    outcome: str = "success",
    detail: dict | None = None,
) -> None:
    db.add(ApiAuditEvent(
        request_id=request_id(request),
        client_id=client.id if client else None,
        action=action,
        entity_type=entity_type,
        entity_key=entity_key,
        outcome=outcome,
        detail_json=detail or {},
    ))


def request_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def find_idempotent(
    db: Session,
    *,
    client: ApiClient,
    request: Request,
    key: str,
    payload: dict,
) -> ApiIdempotencyRecord | None:
    if not key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Idempotency-Key required")
    record = db.scalar(select(ApiIdempotencyRecord).where(
        ApiIdempotencyRecord.client_id == client.id,
        ApiIdempotencyRecord.idempotency_key == key,
        ApiIdempotencyRecord.method == request.method,
        ApiIdempotencyRecord.path == request.url.path,
    ))
    digest = request_hash(payload)
    if record and record.request_hash != digest:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Idempotency key reused with different payload")
    return record


def save_idempotent(
    db: Session,
    *,
    client: ApiClient,
    request: Request,
    key: str,
    payload: dict,
    response: dict,
    status_code: int,
) -> None:
    db.add(ApiIdempotencyRecord(
        client_id=client.id,
        idempotency_key=key,
        method=request.method,
        path=request.url.path,
        request_hash=request_hash(payload),
        response_json=response,
        status_code=status_code,
    ))
