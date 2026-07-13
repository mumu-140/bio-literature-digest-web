from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models import LiteraturePushV2
from .push_email import PushEmailError, send_push_email


MAX_EMAIL_ATTEMPTS = 3


def process_push_email_jobs(db: Session, *, limit: int = 10) -> int:
    """Send queued push emails and persist retryable delivery state."""
    jobs = list(db.scalars(
        select(LiteraturePushV2)
        .options(
            joinedload(LiteraturePushV2.literature_item),
            joinedload(LiteraturePushV2.recipient),
            joinedload(LiteraturePushV2.sender),
        )
        .where(
            LiteraturePushV2.email_notification_status.in_(("pending", "retrying")),
            LiteraturePushV2.email_notification_attempts < MAX_EMAIL_ATTEMPTS,
        )
        .order_by(LiteraturePushV2.id)
        .limit(limit)
    ))
    for job in jobs:
        job.email_notification_attempts += 1
        if job.literature_item is None:
            job.email_notification_status = "failed"
            job.email_notification_error = "Push item missing local content"
            continue
        try:
            send_push_email(
                recipient=job.recipient,
                sender=job.sender,
                paper=job.literature_item,
                note=job.note,
            )
        except (PushEmailError, OSError, TimeoutError) as exc:
            job.email_notification_error = str(exc)[:2000]
            job.email_notification_status = (
                "failed" if job.email_notification_attempts >= MAX_EMAIL_ATTEMPTS else "retrying"
            )
        else:
            job.email_notification_status = "sent"
            job.email_notification_error = ""
            job.email_notification_sent_at = datetime.utcnow()
    db.commit()
    return len(jobs)
