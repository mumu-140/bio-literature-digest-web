from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..deps import get_current_user, get_db
from ..models import PaperPush, User
from ..schemas import PaperPushRead, PaperPushUpdate
from ..services.user_visibility import require_visible_target_user

router = APIRouter(prefix="/pushes", tags=["pushes"])


def serialize_push(push: PaperPush) -> PaperPushRead:
    return PaperPushRead(
        id=push.id,
        paper_id=push.paper_id,
        recipient_user_id=push.recipient_user_id,
        sent_by_user_id=push.sent_by_user_id,
        note=push.note,
        is_read=push.is_read,
        pushed_at=push.pushed_at,
        read_at=push.read_at,
        title_en=push.paper.title_en,
        title_zh=push.paper.title_zh,
        journal=push.paper.journal,
        publish_date=push.paper.publish_date,
        article_url=push.paper.article_url,
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
            select(PaperPush)
            .options(
                joinedload(PaperPush.paper),
                joinedload(PaperPush.sender),
                joinedload(PaperPush.recipient),
            )
            .where(PaperPush.recipient_user_id == target_user_id)
            .order_by(PaperPush.pushed_at.desc())
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
        select(PaperPush)
        .options(joinedload(PaperPush.paper), joinedload(PaperPush.sender), joinedload(PaperPush.recipient))
        .where(PaperPush.id == push_id)
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
