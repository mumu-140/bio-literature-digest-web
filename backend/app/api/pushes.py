from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..deps import get_current_user, get_db
from ..models import LiteraturePushV2, User
from ..schemas import PaperPushRead, PaperPushUpdate
from ..services.user_visibility import require_visible_target_user

router = APIRouter(prefix="/pushes", tags=["pushes"])


def serialize_push(push: LiteraturePushV2) -> PaperPushRead:
    if push.literature_item is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Push item missing local content")
    return PaperPushRead(
        id=push.id,
        paper_id=push.literature_item.id,
        canonical_key=push.literature_item_key,
        recipient_user_id=push.recipient_user_id,
        sent_by_user_id=push.sent_by_user_id,
        note=push.note,
        is_read=push.is_read,
        pushed_at=push.pushed_at,
        read_at=push.read_at,
        title_en=push.literature_item.title_en,
        title_zh=push.literature_item.title_zh,
        journal=push.literature_item.journal,
        publish_date=push.literature_item.publish_date,
        article_url=push.literature_item.article_url,
        sender_name=push.sender.name,
        recipient_name=push.recipient.name,
    )


@router.get("", response_model=list[PaperPushRead])
def list_pushes(
    user_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PaperPushRead]:
    if user_id is None or user_id == current_user.id:
        target_user_id = current_user.id
    elif current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access other users' pushes")
    else:
        target_user_id = require_visible_target_user(db, current_user, user_id).id
    pushes = list(
        db.scalars(
            select(LiteraturePushV2)
            .options(
                joinedload(LiteraturePushV2.literature_item),
                joinedload(LiteraturePushV2.sender),
                joinedload(LiteraturePushV2.recipient),
            )
            .where(LiteraturePushV2.recipient_user_id == target_user_id)
            .order_by(LiteraturePushV2.pushed_at.desc())
        )
    )
    return [serialize_push(push) for push in pushes]


@router.patch("/{push_id}", response_model=PaperPushRead)
def update_push(
    push_id: int,
    payload: PaperPushUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaperPushRead:
    push = db.scalar(
        select(LiteraturePushV2)
        .options(
            joinedload(LiteraturePushV2.literature_item),
            joinedload(LiteraturePushV2.sender),
            joinedload(LiteraturePushV2.recipient),
        )
        .where(LiteraturePushV2.id == push_id)
    )
    if push is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Push not found")
    if current_user.role != "admin" and push.recipient_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify this push")
    if current_user.role == "admin":
        require_visible_target_user(db, current_user, push.recipient_user_id)
    push.is_read = payload.is_read
    push.read_at = datetime.utcnow() if payload.is_read else None
    db.commit()
    db.refresh(push)
    return serialize_push(push)
