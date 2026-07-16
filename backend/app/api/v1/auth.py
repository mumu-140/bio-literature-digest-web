from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config import get_settings
from ...deps import get_db
from ...models import ApiClient, Session as UserSession, User
from ...schemas import DeerFlowSsoIssueRequest, DeerFlowSsoIssueResponse
from ...security import create_session_token
from ...services.api_auth import require_api_scopes
from ...services.audit import record_action
from ...services.user_sync import derive_display_name

router = APIRouter(prefix="/auth", tags=["api-v1-auth"])


def _safe_next_path(value: str) -> str:
    return value if value.startswith("/") and not value.startswith("//") else "/papers/published"


@router.post("/deerflow-sso", response_model=DeerFlowSsoIssueResponse)
def issue_deerflow_sso(
    payload: DeerFlowSsoIssueRequest,
    _: ApiClient = Depends(require_api_scopes("auth:sso")),
    db: Session = Depends(get_db),
) -> DeerFlowSsoIssueResponse:
    settings = get_settings()
    email = str(payload.email).lower()
    user = db.scalar(select(User).where(User.email == email))
    created_user = False
    if user is None:
        user = User(
            email=email,
            name=payload.name.strip() or derive_display_name(email),
            password_hash="passwordless",
            role="member",
            user_group="internal",
            is_active=True,
            must_change_password=False,
        )
        db.add(user)
        db.flush()
        created_user = True
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    ticket, ticket_hash, expires_at = create_session_token(
        ttl_seconds=settings.deerflow_sso_ticket_ttl_seconds,
    )
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=ticket_hash,
            auth_method="deerflow-pending",
            expires_at=expires_at,
        )
    )
    record_action(
        db,
        action_type="deerflow_sso_issued",
        target_user_id=user.id,
        entity_type="session",
        detail={
            "deerflow_subject": payload.subject,
            "created_user": created_user,
            "next_path": _safe_next_path(payload.next_path),
            "expires_at": expires_at.isoformat(),
        },
    )
    db.commit()
    return DeerFlowSsoIssueResponse(
        ticket=ticket,
        consume_url=f"{settings.web_base_url.rstrip('/')}/api/auth/deerflow-sso/consume",
        expires_in=settings.deerflow_sso_ticket_ttl_seconds,
        created_user=created_user,
    )
