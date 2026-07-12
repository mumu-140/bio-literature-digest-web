from __future__ import annotations

from datetime import date as date_type, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..deps import get_current_user, get_db
from ..models import ImportedDigestMembership, ImportedLiteratureItem, User, UserLiteratureFavorite
from ..schemas import DigestPaper, PaginatedPapers, PaperLibraryGroup, PaperLibraryOverview
from ..services.paper_library import (
    PaperLibraryFilters,
    build_digest_paper,
    build_paper_library_overview,
    load_paper_library_group,
    normalize_library_sort,
)

router = APIRouter(tags=["digests"])


def today_cst() -> str:
    settings = get_settings()
    return datetime.now(ZoneInfo(settings.cst_timezone)).strftime("%Y-%m-%d")


def build_paper_rows(db: Session, user_id: int, statement, page: int, page_size: int) -> PaginatedPapers:
    total = db.scalar(select(func.count()).select_from(statement.subquery()))
    rows = db.execute(statement.offset((page - 1) * page_size).limit(page_size)).all()
    item_keys = [row.ImportedLiteratureItem.literature_item_key for row in rows]
    favorite_keys = (
        {
            key
            for (key,) in db.execute(
                select(UserLiteratureFavorite.literature_item_key).where(
                    UserLiteratureFavorite.user_id == user_id,
                    UserLiteratureFavorite.literature_item_key.in_(item_keys),
                )
            ).all()
        }
        if item_keys
        else set()
    )
    items = [build_digest_paper(row, favorite_keys) for row in rows]
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
        select(ImportedLiteratureItem, ImportedDigestMembership)
        .join(ImportedDigestMembership, ImportedDigestMembership.literature_item_id == ImportedLiteratureItem.id)
        .where(
            ImportedDigestMembership.digest_date == digest_date,
            ImportedDigestMembership.list_type == "digest",
        )
        .order_by(ImportedDigestMembership.row_index.asc())
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
    statement = (
        select(ImportedLiteratureItem, ImportedDigestMembership)
        .join(ImportedDigestMembership, ImportedDigestMembership.literature_item_id == ImportedLiteratureItem.id)
        .where(ImportedDigestMembership.list_type == "digest")
    )
    filters = []
    if date:
        filters.append(ImportedDigestMembership.digest_date == date_type.fromisoformat(date))
    if category:
        filters.append(ImportedLiteratureItem.category == category)
    if journal:
        filters.append(ImportedLiteratureItem.journal == journal)
    if interest_level:
        filters.append(ImportedLiteratureItem.interest_level == interest_level)
    if q:
        like_value = f"%{q}%"
        filters.append(
            or_(
                ImportedLiteratureItem.title_en.ilike(like_value),
                ImportedLiteratureItem.title_zh.ilike(like_value),
                ImportedLiteratureItem.summary_zh.ilike(like_value),
                ImportedLiteratureItem.abstract.ilike(like_value),
                ImportedLiteratureItem.journal.ilike(like_value),
                ImportedLiteratureItem.interest_tag.ilike(like_value),
            )
        )
    if filters:
        statement = statement.where(and_(*filters))
    statement = statement.order_by(
        ImportedDigestMembership.digest_date.desc(),
        ImportedLiteratureItem.interest_score.desc(),
        ImportedLiteratureItem.id.desc(),
    )
    return build_paper_rows(db, current_user.id, statement, page, page_size)


@router.get("/papers/library", response_model=PaperLibraryOverview)
def get_paper_library_overview(
    q: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    publish_date: Optional[str] = None,
    sort: str = Query(default="publish_date_desc"),
    initial_group_count: int = Query(default=3, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaperLibraryOverview:
    return build_paper_library_overview(
        db,
        current_user.id,
        PaperLibraryFilters(
            query=q or "",
            category=category or "",
            tag=tag or "",
            publish_date=publish_date or "",
            sort=normalize_library_sort(sort),
        ),
        initial_group_count=initial_group_count,
    )


@router.get("/papers/library/groups/{publish_date}", response_model=PaperLibraryGroup)
def get_paper_library_group(
    publish_date: str,
    q: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    sort: str = Query(default="publish_date_desc"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaperLibraryGroup:
    return load_paper_library_group(
        db,
        current_user.id,
        PaperLibraryFilters(
            query=q or "",
            category=category or "",
            tag=tag or "",
            publish_date="",
            sort=normalize_library_sort(sort),
        ),
        publish_date=publish_date,
    )
