from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import case, exists, func, or_, select
from sqlalchemy.orm import Session

from ..models import ImportedDigestMembership, ImportedLiteratureItem, UserLiteratureFavorite
from ..schemas import DigestPaper


UNKNOWN_PUBLISH_DATE = "unknown"


def load_group_page(
    db: Session,
    user_id: int,
    filters,
    *,
    page: int,
    page_size: int,
    apply_text_filter: Callable,
    build_paper: Callable,
) -> tuple[int, list[DigestPaper]]:
    """Load one priority-ordered publication-date page without scanning the full group."""
    id_statement = _group_id_statement(db, filters, apply_text_filter)
    paper_count = int(db.scalar(select(func.count()).select_from(id_statement.subquery())) or 0)
    page_ids = list(db.scalars(
        id_statement
        .order_by(*_priority_expressions())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ))
    if not page_ids:
        return paper_count, []

    rows = _dedupe_rows(db.execute(
        select(ImportedLiteratureItem, ImportedDigestMembership)
        .join(ImportedDigestMembership, ImportedDigestMembership.literature_item_id == ImportedLiteratureItem.id)
        .where(
            ImportedDigestMembership.list_type == "digest",
            ImportedLiteratureItem.id.in_(page_ids),
        )
        .order_by(ImportedDigestMembership.digest_date.desc())
    ).all())
    rows_by_id = {row.ImportedLiteratureItem.id: row for row in rows}
    ordered_rows = [rows_by_id[paper_id] for paper_id in page_ids if paper_id in rows_by_id]
    favorite_keys = _favorite_keys(
        db,
        user_id,
        [row.ImportedLiteratureItem.literature_item_key for row in ordered_rows],
    )
    return paper_count, [build_paper(row, favorite_keys) for row in ordered_rows]


def _group_id_statement(db: Session, filters, apply_text_filter: Callable):
    statement = (
        select(ImportedLiteratureItem.id)
        .join(ImportedDigestMembership, ImportedDigestMembership.literature_item_id == ImportedLiteratureItem.id)
        .where(ImportedDigestMembership.list_type == "digest")
        .group_by(ImportedLiteratureItem.id)
    )
    if filters.category:
        statement = statement.where(ImportedLiteratureItem.category == filters.category)
    if filters.query:
        statement = apply_text_filter(db, statement, filters.query)
    if filters.publish_date == UNKNOWN_PUBLISH_DATE:
        valid_date = ImportedLiteratureItem.publish_date.op("GLOB")("????-??-??*")
        statement = statement.where(or_(
            ImportedLiteratureItem.publish_date.is_(None),
            func.trim(ImportedLiteratureItem.publish_date) == "",
            ~valid_date,
        ))
    elif filters.publish_date:
        statement = statement.where(ImportedLiteratureItem.publish_date.like(f"{filters.publish_date}%"))
    if filters.tag:
        tag_values = func.json_each(ImportedLiteratureItem.tags_json).table_valued("key", "value").alias("tag_values")
        statement = statement.where(exists(
            select(1).select_from(tag_values).where(tag_values.c.value == filters.tag)
        ))
    return statement


def _priority_expressions() -> tuple[Any, ...]:
    journal = func.lower(func.trim(ImportedLiteratureItem.journal))
    flagship_rank = case(
        (journal == "cell", 0),
        (journal == "nature", 1),
        (journal == "science", 2),
        else_=3,
    )
    interest_rank = case(
        (ImportedLiteratureItem.interest_level.contains("非常感兴趣"), 0),
        (ImportedLiteratureItem.interest_level.contains("感兴趣"), 1),
        (ImportedLiteratureItem.interest_level.contains("一般"), 2),
        else_=9,
    )
    return (
        flagship_rank.asc(),
        interest_rank.asc(),
        ImportedLiteratureItem.interest_score.desc(),
        ImportedLiteratureItem.id.desc(),
    )


def _dedupe_rows(rows) -> list:
    latest_by_item_id = {}
    for row in rows:
        latest_by_item_id.setdefault(row.ImportedLiteratureItem.id, row)
    return list(latest_by_item_id.values())


def _favorite_keys(db: Session, user_id: int, item_keys: list[str]) -> set[str]:
    if not item_keys:
        return set()
    return {
        key
        for (key,) in db.execute(
            select(UserLiteratureFavorite.literature_item_key).where(
                UserLiteratureFavorite.user_id == user_id,
                UserLiteratureFavorite.literature_item_key.in_(item_keys),
            )
        ).all()
    }
