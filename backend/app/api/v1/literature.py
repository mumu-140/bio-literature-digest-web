from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ...api_v1_schemas import LiteratureBatchRequest
from ...deps import get_db
from ...models import ApiClient, ImportedLiteratureItem
from ...services.api_auth import require_api_scopes

router = APIRouter(prefix="/literature", tags=["api-v1-literature"])


def serialize(item: ImportedLiteratureItem) -> dict:
    return {
        "id": item.id,
        "key": item.literature_item_key,
        "doi": item.doi,
        "title_en": item.title_en,
        "title_zh": item.title_zh,
        "authors": item.authors_json or [],
        "journal": item.journal,
        "publish_date": item.publish_date,
        "category": item.category,
        "interest_level": item.interest_level,
        "interest_score": item.interest_score,
        "interest_tag": item.interest_tag,
        "abstract": item.abstract,
        "summary_zh": item.summary_zh,
        "article_url": item.article_url,
        "tags": item.tags_json or [],
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


@router.get("")
def search_literature(
    q: str = "",
    category: str = "",
    published_from: str = "",
    published_to: str = "",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _: ApiClient = Depends(require_api_scopes("literature:read")),
    db: Session = Depends(get_db),
) -> dict:
    statement = select(ImportedLiteratureItem)
    filters = []
    if q.strip():
        like = f"%{q.strip()}%"
        filters.append(or_(
            ImportedLiteratureItem.title_en.ilike(like),
            ImportedLiteratureItem.title_zh.ilike(like),
            ImportedLiteratureItem.abstract.ilike(like),
            ImportedLiteratureItem.summary_zh.ilike(like),
            ImportedLiteratureItem.journal.ilike(like),
            ImportedLiteratureItem.doi.ilike(like),
        ))
    if category:
        filters.append(ImportedLiteratureItem.category == category)
    if published_from:
        filters.append(ImportedLiteratureItem.publish_date >= published_from)
    if published_to:
        filters.append(ImportedLiteratureItem.publish_date <= published_to)
    if filters:
        statement = statement.where(*filters)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    items = list(db.scalars(
        statement.order_by(ImportedLiteratureItem.publish_date.desc(), ImportedLiteratureItem.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ))
    return {"api_version": "v1", "total": total, "page": page, "page_size": page_size, "items": [serialize(item) for item in items]}


@router.post("/batch")
def batch_literature(
    payload: LiteratureBatchRequest,
    _: ApiClient = Depends(require_api_scopes("literature:read")),
    db: Session = Depends(get_db),
) -> dict:
    items = list(db.scalars(select(ImportedLiteratureItem).where(
        ImportedLiteratureItem.literature_item_key.in_(payload.keys)
    )))
    by_key = {item.literature_item_key: item for item in items}
    return {"api_version": "v1", "items": [serialize(by_key[key]) for key in payload.keys if key in by_key]}
