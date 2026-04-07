from __future__ import annotations

from datetime import date as date_type, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..deps import get_current_user, get_db
from ..models import Favorite, Paper, PaperDailyEntry, User
from ..schemas import DigestPaper, PaginatedPapers

router = APIRouter(tags=["digests"])


def today_cst() -> str:
    settings = get_settings()
    return datetime.now(ZoneInfo(settings.cst_timezone)).strftime("%Y-%m-%d")


def build_paper_rows(db: Session, user_id: int, statement, page: int, page_size: int) -> PaginatedPapers:
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    rows = db.execute(statement.offset((page - 1) * page_size).limit(page_size)).all()
    paper_ids = [row.Paper.id for row in rows]
    favorite_ids = (
        {
            paper_id
            for (paper_id,) in db.execute(select(Favorite.paper_id).where(Favorite.user_id == user_id, Favorite.paper_id.in_(paper_ids))).all()
        }
        if rows
        else set()
    )
    items = [
        DigestPaper(
            id=row.Paper.id,
            digest_date=str(row.PaperDailyEntry.digest_date),
            doi=row.Paper.doi,
            journal=row.Paper.journal,
            publish_date=row.Paper.publish_date,
            category=row.Paper.category,
            interest_level=row.Paper.interest_level,
            interest_score=row.Paper.interest_score,
            interest_tag=row.Paper.interest_tag,
            title_en=row.Paper.title_en,
            title_zh=row.Paper.title_zh,
            summary_zh=row.Paper.summary_zh,
            abstract=row.Paper.abstract,
            article_url=row.Paper.article_url,
            publication_stage=row.PaperDailyEntry.publication_stage,
            tags=row.Paper.tags_json or [],
            is_favorited=row.Paper.id in favorite_ids,
        )
        for row in rows
    ]
    return PaginatedPapers(items=items, total=int(total or 0), page=page, page_size=page_size)


@router.get("/digests/today", response_model=PaginatedPapers)
def get_today_digest(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedPapers:
    return get_digest_by_date(date=today_cst(), page=page, page_size=page_size, current_user=current_user, db=db)


@router.get("/digests", response_model=PaginatedPapers)
def get_digest_by_date(
    date: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedPapers:
    digest_date = date_type.fromisoformat(date)
    statement = (
        select(Paper, PaperDailyEntry)
        .join(PaperDailyEntry, PaperDailyEntry.paper_id == Paper.id)
        .where(PaperDailyEntry.digest_date == digest_date)
        .order_by(PaperDailyEntry.row_index.asc())
    )
    return build_paper_rows(db, current_user.id, statement, page, page_size)


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
    db: Session = Depends(get_db),
) -> PaginatedPapers:
    statement = select(Paper, PaperDailyEntry).join(PaperDailyEntry, PaperDailyEntry.paper_id == Paper.id)
    filters = []
    if date:
        filters.append(PaperDailyEntry.digest_date == date_type.fromisoformat(date))
    if category:
        filters.append(Paper.category == category)
    if journal:
        filters.append(Paper.journal == journal)
    if interest_level:
        filters.append(Paper.interest_level == interest_level)
    if q:
        like_value = f"%{q}%"
        filters.append(
            or_(
                Paper.title_en.ilike(like_value),
                Paper.title_zh.ilike(like_value),
                Paper.summary_zh.ilike(like_value),
                Paper.abstract.ilike(like_value),
                Paper.journal.ilike(like_value),
            )
        )
    if filters:
        statement = statement.where(and_(*filters))
    statement = statement.order_by(PaperDailyEntry.digest_date.desc(), Paper.interest_score.desc(), Paper.id.desc())
    return build_paper_rows(db, current_user.id, statement, page, page_size)
