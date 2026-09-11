from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...deps import get_db
from ...models import ApiAuditEvent, ApiClient
from ...services.api_auth import require_api_scopes

router = APIRouter(prefix="/audit-events", tags=["api-v1-audit"])


@router.get("")
def list_audit_events(
    limit: int = Query(default=100, ge=1, le=500),
    client: ApiClient = Depends(require_api_scopes("audit:read")),
    db: Session = Depends(get_db),
) -> dict:
    items = list(db.scalars(
        select(ApiAuditEvent)
        .where((ApiAuditEvent.client_id == client.id) | (ApiAuditEvent.client_id.is_(None)))
        .order_by(ApiAuditEvent.id.desc()).limit(limit)
    ))
    return {"items": [{
        "request_id": item.request_id,
        "action": item.action,
        "entity_type": item.entity_type,
        "entity_key": item.entity_key,
        "outcome": item.outcome,
        "detail": item.detail_json,
        "created_at": item.created_at.isoformat(),
    } for item in items]}
