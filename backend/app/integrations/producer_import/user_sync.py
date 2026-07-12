from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import User
from ...services.user_sync import UserSyncResult, derive_display_name, read_users_config, sync_users_from_config


def sync_users_from_producer_config(db: Session, *, config_path: Path) -> UserSyncResult:
    result = sync_users_from_config(db, config_path=config_path)
    records = read_users_config(config_path)
    if not records:
        return result
    by_email = {str(record.get("email") or "").strip().lower(): str(record.get("uid") or "").strip() for record in records}
    users = list(db.scalars(select(User).where(User.email.in_(tuple(by_email.keys())))))
    changed = False
    for user in users:
        uid = by_email.get(user.email.lower(), "")
        if uid and user.producer_uid != uid:
            user.producer_uid = uid
            changed = True
        if not user.name:
            user.name = derive_display_name(user.email)
            changed = True
    if changed:
        db.commit()
    return result
