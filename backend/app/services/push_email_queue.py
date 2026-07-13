from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from ..models import LiteraturePushV2
from .push_email import PushEmailError, send_push_email, send_push_email_batch


MAX_EMAIL_ATTEMPTS = 3
QUEUED_STATUSES = ("pending", "retrying")


def process_push_email_jobs(db: Session, *, limit: int = 10) -> int:
    """Send queued push emails and persist retryable delivery state."""
    seed_jobs = _load_jobs(db, limit=limit)
    groups = _expand_job_groups(db, seed_jobs)
    for jobs in groups:
        _process_job_group(jobs)
    db.commit()
    return sum(len(jobs) for jobs in groups)


def _load_jobs(db: Session, *, limit: int) -> list[LiteraturePushV2]:
    return list(db.scalars(
        _job_statement()
        .order_by(LiteraturePushV2.id)
        .limit(limit)
    ))


def _job_statement():
    return (
        select(LiteraturePushV2)
        .options(
            joinedload(LiteraturePushV2.literature_item),
            joinedload(LiteraturePushV2.recipient),
            joinedload(LiteraturePushV2.sender),
        )
        .where(
            LiteraturePushV2.email_notification_status.in_(QUEUED_STATUSES),
            LiteraturePushV2.email_notification_attempts < MAX_EMAIL_ATTEMPTS,
        )
    )


def _expand_job_groups(
    db: Session,
    seed_jobs: list[LiteraturePushV2],
) -> list[list[LiteraturePushV2]]:
    groups: list[list[LiteraturePushV2]] = []
    seen: set[tuple[str, int]] = set()
    for job in seed_jobs:
        key = (job.batch_id, job.recipient_user_id) if job.batch_id else ("single", job.id)
        if key in seen:
            continue
        seen.add(key)
        if not job.batch_id:
            groups.append([job])
            continue
        groups.append(list(db.scalars(
            _job_statement().where(
                LiteraturePushV2.batch_id == job.batch_id,
                LiteraturePushV2.recipient_user_id == job.recipient_user_id,
            ).order_by(LiteraturePushV2.id)
        )))
    return groups


def _process_job_group(jobs: list[LiteraturePushV2]) -> None:
    for job in jobs:
        job.email_notification_attempts += 1
    if any(job.literature_item is None for job in jobs):
        _mark_failed(jobs, "Push item missing local content")
        return
    first = jobs[0]
    try:
        if first.batch_id:
            send_push_email_batch(
                recipient=first.recipient,
                sender=first.sender,
                papers=[job.literature_item for job in jobs if job.literature_item is not None],
                note=first.note,
            )
        else:
            send_push_email(
                recipient=first.recipient,
                sender=first.sender,
                paper=first.literature_item,
                note=first.note,
            )
    except (PushEmailError, OSError, TimeoutError) as exc:
        _mark_failed(jobs, str(exc)[:2000])
        return
    sent_at = datetime.utcnow()
    for job in jobs:
        job.email_notification_status = "sent"
        job.email_notification_error = ""
        job.email_notification_sent_at = sent_at


def _mark_failed(jobs: list[LiteraturePushV2], error: str) -> None:
    for job in jobs:
        job.email_notification_error = error
        job.email_notification_status = (
            "failed" if job.email_notification_attempts >= MAX_EMAIL_ATTEMPTS else "retrying"
        )
