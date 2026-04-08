from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_db, require_admin
from ..models import Paper, PaperPush, User
from ..schemas import PaperPushCreate, PaperPushRead, UserCreate, UserRead, UserUpdate
from ..services.audit import record_action
from ..services.user_visibility import require_visible_target_user, visible_user_statement
from ..services.user_sync import derive_display_name

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserRead])
def list_users(current_user: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(visible_user_statement(current_user).order_by(User.created_at.asc())))


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)) -> User:
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    normalized_email = payload.email.lower()
    resolved_group = payload.user_group or "internal"
    user = User(
        email=normalized_email,
        name=(payload.name or "").strip() or derive_display_name(normalized_email),
        password_hash="passwordless",
        role=payload.role,
        user_group=resolved_group,
        owner_admin_user_id=current_user.id if resolved_group == "outsider" else None,
        is_active=payload.is_active,
        must_change_password=False,
    )
    db.add(user)
    db.flush()
    record_action(
        db,
        action_type="admin_create_user",
        actor_user_id=current_user.id,
        target_user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        detail={"email": user.email, "role": user.role, "user_group": user.user_group},
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(user_id: int, payload: UserUpdate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)) -> User:
    user = require_visible_target_user(db, current_user, user_id)
    for field in ("name", "role", "user_group", "owner_admin_user_id", "is_active"):
        value = getattr(payload, field)
        if value is not None:
            setattr(user, field, value)
    user.name = (user.name or "").strip() or derive_display_name(user.email)
    if user.user_group != "outsider":
        user.owner_admin_user_id = None
    elif user.owner_admin_user_id is None:
        user.owner_admin_user_id = current_user.id
    record_action(
        db,
        action_type="admin_update_user",
        actor_user_id=current_user.id,
        target_user_id=user.id,
        entity_type="user",
        entity_id=user.id,
        detail=payload.model_dump(exclude_none=True),
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/pushes", response_model=PaperPushRead, status_code=status.HTTP_201_CREATED)
def push_paper_to_user(
    payload: PaperPushCreate,
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PaperPushRead:
    recipient = require_visible_target_user(db, admin_user, payload.recipient_user_id)
    paper = db.get(Paper, payload.paper_id)
    if paper is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paper not found")
    push = PaperPush(
        paper_id=paper.id,
        recipient_user_id=recipient.id,
        sent_by_user_id=admin_user.id,
        note=payload.note.strip(),
    )
    db.add(push)
    record_action(
        db,
        action_type="admin_push_paper",
        actor_user_id=admin_user.id,
        target_user_id=recipient.id,
        entity_type="paper",
        entity_id=paper.id,
        detail={"note": payload.note.strip()},
    )
    db.commit()
    db.refresh(push)
    return PaperPushRead(
        id=push.id,
        paper_id=paper.id,
        recipient_user_id=recipient.id,
        sent_by_user_id=admin_user.id,
        note=push.note,
        is_read=push.is_read,
        pushed_at=push.pushed_at,
        read_at=push.read_at,
        title_en=paper.title_en,
        title_zh=paper.title_zh,
        journal=paper.journal,
        publish_date=paper.publish_date,
        article_url=paper.article_url,
        sender_name=admin_user.name,
        recipient_name=recipient.name,
    )
