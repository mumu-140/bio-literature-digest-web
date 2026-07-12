from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from ..models import User


OUTSIDER_GROUP = "outsider"
INTERNAL_GROUP = "internal"


def visible_user_statement(current_user: User) -> Select[tuple[User]]:
    statement = select(User)
    if current_user.role != "admin":
        return statement.where(User.id == current_user.id)
    return statement.where(
        or_(
            User.user_group != OUTSIDER_GROUP,
            User.owner_admin_user_id == current_user.id,
            User.id == current_user.id,
        )
    )


def admin_can_access_user(current_user: User, target_user: User) -> bool:
    if current_user.role != "admin":
        return current_user.id == target_user.id
    if target_user.id == current_user.id:
        return True
    if target_user.user_group != OUTSIDER_GROUP:
        return True
    return target_user.owner_admin_user_id == current_user.id


def require_visible_target_user(db: Session, current_user: User, target_user_id: int) -> User:
    target_user = db.get(User, target_user_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not admin_can_access_user(current_user, target_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return target_user
