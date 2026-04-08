from __future__ import annotations

from datetime import date as date_type, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..deps import get_current_user, get_shared_db
from ..models import User
from ..schemas import DigestPaper, PaginatedPapers
from ..shared_models import SharedActor, SharedActorFavorite, SharedDigestMembership, SharedLiteratureItem

router = APIRouter(tags=["digests"])


def today_cst() -> str:
    settings = get_settings()
    return datetime.now(ZoneInfo(settings.cst_timezone)).strftime("%Y-%m-%d")


def _actor_for_user(db: Session, user: User) -> SharedActor | None:
    return db.scalar(select(SharedActor).where(SharedActor.actor_key == user.email.lower()))


def build_paper_rows(db: Session, actor_id: Optional[int], statement, page: int, page_size: int) -> PaginatedPapers:
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    rows = db.execute(statement.offset((page - 1) * page_size).limit(page_size)).all()
    paper_ids = [row.SharedLiteratureItem.id for row in rows]
    favorite_ids = (
        {
            item_id
            for (item_id,) in db.execute(
                select(SharedActorFavorite.item_id).where(
                    SharedActorFavorite.actor_id == actor_id,
                    SharedActorFavorite.item_id.in_(paper_ids),
                )
            ).all()
        }
        if rows and actor_id is not None
        else set()
    )
    items = [
        DigestPaper(
            id=row.SharedLiteratureItem.id,
            digest_date=str(row.SharedDigestMembership.digest_date),
            doi=row.SharedLiteratureItem.doi,
            journal=row.SharedLiteratureItem.journal,
            publish_date=row.SharedLiteratureItem.publish_date,
            category=row.SharedLiteratureItem.category,
            interest_level=row.SharedLiteratureItem.interest_level,
            interest_score=row.SharedLiteratureItem.interest_score,
            interest_tag=row.SharedLiteratureItem.interest_tag,
            title_en=row.SharedLiteratureItem.title_en,
            title_zh=row.SharedLiteratureItem.title_zh,
            summary_zh=row.SharedLiteratureItem.summary_zh,
            abstract=row.SharedLiteratureItem.abstract,
            article_url=row.SharedLiteratureItem.article_url,
            publication_stage=row.SharedDigestMembership.publication_stage,
            tags=row.SharedLiteratureItem.tags_json or [],
            is_favorited=row.SharedLiteratureItem.id in favorite_ids,
        )
        for row in rows
    ]
    return PaginatedPapers(items=items, total=int(total or 0), page=page, page_size=page_size)


@router.get("/digests/today", response_model=PaginatedPapers)
def get_today_digest(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_shared_db),
) -> PaginatedPapers:
    return get_digest_by_date(date=today_cst(), page=page, page_size=page_size, current_user=current_user, db=db)


@router.get("/digests", response_model=PaginatedPapers)
def get_digest_by_date(
    date: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_shared_db),
) -> PaginatedPapers:
    digest_date = date_type.fromisoformat(date)
    actor = _actor_for_user(db, current_user)
    statement = (
        select(SharedLiteratureItem, SharedDigestMembership)
        .join(SharedDigestMembership, SharedDigestMembership.item_id == SharedLiteratureItem.id)
        .where(
            SharedDigestMembership.digest_date == digest_date,
            SharedDigestMembership.list_type == "digest",
        )
        .order_by(SharedDigestMembership.row_index.asc())
    )
    return build_paper_rows(db, actor.id if actor else None, statement, page, page_size)


@router.get("/papers", response_model=PaginatedPapers)
def list_papers(
    date: Optional[str] = None,
    category: Optional[str] = None,
    journal: Optional[str] = None,
    interest_level: Optional[str] = None,
    q: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_shared_db),
) -> PaginatedPapers:
    actor = _actor_for_user(db, current_user)
    statement = (
        select(SharedLiteratureItem, SharedDigestMembership)
        .join(SharedDigestMembership, SharedDigestMembership.item_id == SharedLiteratureItem.id)
        .where(SharedDigestMembership.list_type == "digest")
    )
    filters = []
    if date:
        filters.append(SharedDigestMembership.digest_date == date_type.fromisoformat(date))
    if category:
        filters.append(SharedLiteratureItem.category == category)
    if journal:
        filters.append(SharedLiteratureItem.journal == journal)
    if interest_level:
        filters.append(SharedLiteratureItem.interest_level == interest_level)
    if q:
        like_value = f"%{q}%"
        filters.append(
            or_(
                SharedLiteratureItem.title_en.ilike(like_value),
                SharedLiteratureItem.title_zh.ilike(like_value),
                SharedLiteratureItem.summary_zh.ilike(like_value),
                SharedLiteratureItem.abstract.ilike(like_value),
                SharedLiteratureItem.journal.ilike(like_value),
            )
        )
    if filters:
        statement = statement.where(and_(*filters))
    statement = statement.order_by(
        SharedDigestMembership.digest_date.desc(),
        SharedLiteratureItem.interest_score.desc(),
        SharedLiteratureItem.id.desc(),
    )
    return build_paper_rows(db, actor.id if actor else None, statement, page, page_size)
