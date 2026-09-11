from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ImportedLiteratureItem, LiteraturePushV2, User
from .audit import record_action
from .user_visibility import visible_user_statement


MAX_PUSH_COMBINATIONS = 200


class PushRequestError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class PushBatch:
    batch_id: str
    paper_ids: list[int]
    recipient_user_ids: list[int]
    papers: list[ImportedLiteratureItem]
    recipients: list[User]
    pushes: list[LiteraturePushV2]


def dedupe_ids(values: list[int]) -> list[int]:
    return list(dict.fromkeys(values))


def _load_papers(db: Session, paper_ids: list[int]) -> list[ImportedLiteratureItem]:
    papers = list(db.scalars(select(ImportedLiteratureItem).where(ImportedLiteratureItem.id.in_(paper_ids))))
    by_id = {paper.id: paper for paper in papers}
    if any(paper_id not in by_id for paper_id in paper_ids):
        raise PushRequestError(404, "Paper not found")
    return [by_id[paper_id] for paper_id in paper_ids]


def _load_recipients(db: Session, admin_user: User, recipient_ids: list[int]) -> list[User]:
    users = list(db.scalars(visible_user_statement(admin_user).where(User.id.in_(recipient_ids))))
    by_id = {user.id: user for user in users}
    if any(user_id not in by_id for user_id in recipient_ids):
        raise PushRequestError(404, "User not found")
    recipients = [by_id[user_id] for user_id in recipient_ids]
    if any(not user.is_active for user in recipients):
        raise PushRequestError(422, "Recipient user is inactive")
    return recipients



def _record_push_audit(
    db: Session,
    *,
    admin_user: User,
    recipient: User,
    papers: list[ImportedLiteratureItem],
    pushes: list[LiteraturePushV2],
    batch_id: str,
    note: str,
    send_email_notification: bool,
) -> None:
    if not batch_id:
        record_action(
            db,
            action_type="admin_push_paper",
            actor_user_id=admin_user.id,
            target_user_id=recipient.id,
            entity_type="paper",
            entity_id=papers[0].id,
            detail={"note": note.strip(), "canonical_key": papers[0].literature_item_key},
        )
        return
    record_action(
        db,
        action_type="admin_batch_push_papers",
        actor_user_id=admin_user.id,
        target_user_id=recipient.id,
        entity_type="push_batch",
        entity_id=pushes[0].id,
        detail={
            "batch_id": batch_id,
            "paper_ids": [paper.id for paper in papers],
            "push_ids": [push.id for push in pushes],
            "send_email_notification": send_email_notification,
        },
    )

def create_push_batch(
    db: Session,
    *,
    admin_user: User,
    paper_ids: list[int],
    recipient_user_ids: list[int],
    note: str,
    send_email_notification: bool,
    batch_id: str | None = None,
) -> PushBatch:
    normalized_paper_ids = dedupe_ids(paper_ids)
    normalized_recipient_ids = dedupe_ids(recipient_user_ids)
    if len(normalized_paper_ids) * len(normalized_recipient_ids) > MAX_PUSH_COMBINATIONS:
        raise PushRequestError(422, f"Push batch exceeds {MAX_PUSH_COMBINATIONS} combinations")

    papers = _load_papers(db, normalized_paper_ids)
    recipients = _load_recipients(db, admin_user, normalized_recipient_ids)
    resolved_batch_id = str(uuid4()) if batch_id is None else batch_id
    pushes = [
        LiteraturePushV2(
            batch_id=resolved_batch_id,
            literature_item_id=paper.id,
            literature_item_key=paper.literature_item_key,
            recipient_user_id=recipient.id,
            sent_by_user_id=admin_user.id,
            note=note.strip(),
            email_notification_status="pending" if send_email_notification else "not_requested",
        )
        for recipient in recipients
        for paper in papers
    ]
    db.add_all(pushes)
    db.flush()
    for recipient in recipients:
        recipient_pushes = [push for push in pushes if push.recipient_user_id == recipient.id]
        _record_push_audit(
            db,
            admin_user=admin_user,
            recipient=recipient,
            papers=papers,
            pushes=recipient_pushes,
            batch_id=resolved_batch_id,
            note=note,
            send_email_notification=send_email_notification,
        )
    db.commit()
    return PushBatch(
        batch_id=resolved_batch_id,
        paper_ids=normalized_paper_ids,
        recipient_user_ids=normalized_recipient_ids,
        papers=papers,
        recipients=recipients,
        pushes=pushes,
    )
