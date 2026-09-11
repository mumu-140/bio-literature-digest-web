from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...api_v1_schemas import RuleSuggestionCreate
from ...deps import get_db, require_admin
from ...models import ApiClient, ApiRuleSuggestion, User
from ...services.api_auth import require_api_scopes
from ...services.api_support import find_idempotent, record_api_audit, save_idempotent
from ...services.rule_workflow import publish_rules, read_rules

router = APIRouter(tags=["api-v1-rules"])


def serialize(item: ApiRuleSuggestion) -> dict:
    return {
        "id": item.public_id,
        "baseline_sha256": item.baseline_sha256,
        "summary": item.summary,
        "status": item.status,
        "snapshot_path": item.snapshot_path,
        "created_at": item.created_at.isoformat(),
        "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
    }


@router.get("/rules")
def get_rules(
    _: ApiClient = Depends(require_api_scopes("rules:read")),
) -> dict:
    path, content, digest = read_rules()
    return {"api_version": "v1", "path_name": path.name, "content": content, "content_sha256": digest}


@router.post("/rule-suggestions", status_code=status.HTTP_201_CREATED)
def create_suggestion(
    payload: RuleSuggestionCreate,
    request: Request,
    response: Response,
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
    client: ApiClient = Depends(require_api_scopes("rules:suggest")),
    db: Session = Depends(get_db),
) -> dict:
    body = payload.model_dump()
    existing = find_idempotent(db, client=client, request=request, key=idempotency_key, payload=body)
    if existing:
        response.status_code = 200
        return existing.response_json
    suggestion = ApiRuleSuggestion(
        public_id=str(uuid.uuid4()),
        baseline_sha256=payload.baseline_sha256,
        proposed_content=payload.proposed_content,
        summary=payload.summary,
        submitted_by_client_id=client.id,
    )
    db.add(suggestion)
    db.flush()
    result = serialize(suggestion)
    save_idempotent(db, client=client, request=request, key=idempotency_key, payload=body, response=result, status_code=201)
    record_api_audit(db, request=request, client=client, action="rule_suggestion.create", entity_type="rule_suggestion", entity_key=suggestion.public_id)
    db.commit()
    return result


@router.post("/rule-suggestions/{suggestion_id}/publish")
def publish_suggestion(
    suggestion_id: str,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    suggestion = db.scalar(select(ApiRuleSuggestion).where(ApiRuleSuggestion.public_id == suggestion_id))
    if suggestion is None:
        raise HTTPException(status_code=404, detail="Rule suggestion not found")
    if suggestion.status == "published":
        return serialize(suggestion)
    try:
        snapshot = publish_rules(
            proposed_content=suggestion.proposed_content,
            baseline_sha256=suggestion.baseline_sha256,
            suggestion_id=suggestion.public_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    suggestion.status = "published"
    suggestion.reviewed_by_user_id = admin.id
    suggestion.reviewed_at = datetime.utcnow()
    suggestion.snapshot_path = snapshot
    record_api_audit(db, request=request, client=None, action="rule_suggestion.publish", entity_type="rule_suggestion", entity_key=suggestion.public_id, detail={"admin_user_id": admin.id})
    db.commit()
    db.refresh(suggestion)
    return serialize(suggestion)
