from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from ..models import ActionLog


def record_action(
    db: Session,
    *,
    action_type: str,
    actor_user_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    entity_type: str = "",
    entity_id: Optional[int] = None,
    detail: Optional[dict] = None,
) -> ActionLog:
    log = ActionLog(
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        detail_json=detail or {},
    )
    db.add(log)
    return log
