from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date as date_type
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..models import ImportedDigestMembership, ImportedLiteratureItem, UserLiteratureFavorite
from ..schemas import DigestPaper, PaperLibraryGroup, PaperLibraryGroupSummary, PaperLibraryOverview
from .library_stats import load_library_stats
from .search_index import apply_full_text_filter, search_index_available

DEFAULT_LIBRARY_SORT = "publish_date_desc"
SUPPORTED_LIBRARY_SORTS = {"publish_date_desc", "publish_date_asc"}
UNKNOWN_PUBLISH_DATE = "unknown"
FLAGSHIP_JOURNAL_ORDER = ("cell", "nature", "science")

_DATE_PREFIX_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass(frozen=True)
class PaperLibraryFilters:
    query: str = ""
    category: str = ""
    tag: str = ""
    publish_date: str = ""
    sort: str = DEFAULT_LIBRARY_SORT


def normalize_library_sort(value: Optional[str]) -> str:
    if value in SUPPORTED_LIBRARY_SORTS:
        return value
    return DEFAULT_LIBRARY_SORT


def normalize_publish_date(value: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        return UNKNOWN_PUBLISH_DATE
    match = _DATE_PREFIX_PATTERN.search(cleaned)
    if match:
        return match.group(1)
    return cleaned


def build_digest_paper(row, favorite_keys: set[str]) -> DigestPaper:
    paper = row.ImportedLiteratureItem
    membership = row.ImportedDigestMembership
    return DigestPaper(
        id=paper.id,
        canonical_key=paper.literature_item_key,
        digest_date=str(membership.digest_date),
        doi=paper.doi,
        journal=paper.journal,
        publish_date=paper.publish_date,
        publish_date_day=normalize_publish_date(paper.publish_date),
        category=paper.category,
        interest_level=paper.interest_level,
        interest_score=paper.interest_score,
        interest_tag=paper.interest_tag,
        authors=paper.authors_json or [],
        title_en=paper.title_en,
        title_zh=paper.title_zh,
        summary_zh=paper.summary_zh,
        abstract=paper.abstract,
        article_url=paper.article_url,
        publication_stage=membership.publication_stage,
        tags=paper.tags_json or [],
        is_favorited=paper.literature_item_key in favorite_keys,
    )


def build_paper_library_overview(
    db: Session,
    user_id: int,
    filters: PaperLibraryFilters,
    *,
    initial_group_count: int = 3,
) -> PaperLibraryOverview:
    normalized_filters = PaperLibraryFilters(
        query=filters.query.strip(),
        category=filters.category.strip(),
        tag=filters.tag.strip(),
        publish_date=_normalize_requested_publish_date(filters.publish_date),
        sort=normalize_library_sort(filters.sort),
    )
    filter_options = collect_paper_library_filter_options(db)
    stats_rows = load_library_stats(db) if _can_use_materialized_stats(normalized_filters) else []
    if stats_rows:
        group_counts = dict(stats_rows)
        total_papers = sum(group_counts.values())
    else:
        paper_dates = load_paper_library_index(db, normalized_filters)
        group_counts = {date: len(ids) for date, ids in _group_paper_ids_by_publish_date(paper_dates).items()}
        total_papers = len(paper_dates)
    ordered_dates = order_publish_dates(group_counts.keys(), normalized_filters.sort)
    if normalized_filters.publish_date:
        loaded_dates = ordered_dates[:1]
    else:
        safe_group_count = max(1, min(initial_group_count, 10))
        loaded_dates = ordered_dates[:safe_group_count]

    return PaperLibraryOverview(
        total_papers=total_papers,
        available_publish_dates=filter_options["available_publish_dates"],
        available_categories=filter_options["available_categories"],
        available_tags=filter_options["available_tags"],
        groups=[
            PaperLibraryGroupSummary(publish_date=publish_date, paper_count=group_counts[publish_date])
            for publish_date in ordered_dates
        ],
        loaded_groups=[
            PaperLibraryGroup(
                publish_date=publish_date,
                paper_count=group_counts[publish_date],
                items=load_paper_library_group(
                    db,
                    user_id,
                    normalized_filters,
                    publish_date=publish_date,
                    page=1,
                    page_size=50,
                ).items,
                page=1,
                page_size=50,
                has_more=group_counts[publish_date] > 50,
            )
            for publish_date in loaded_dates
        ],
        sort=normalized_filters.sort,
    )


def load_paper_library_group(
    db: Session,
    user_id: int,
    filters: PaperLibraryFilters,
    *,
    publish_date: str,
    page: int = 1,
    page_size: int = 50,
) -> PaperLibraryGroup:
    requested_publish_date = _normalize_requested_publish_date(publish_date)
    normalized_filters = PaperLibraryFilters(
        query=filters.query.strip(),
        category=filters.category.strip(),
        tag=filters.tag.strip(),
        publish_date=requested_publish_date,
        sort=normalize_library_sort(filters.sort),
    )
    papers = load_paper_library_papers(db, user_id, normalized_filters)
    ordered_items = _sort_group_items(papers)
    start = (page - 1) * page_size
    end = start + page_size
    return PaperLibraryGroup(
        publish_date=requested_publish_date,
        paper_count=len(ordered_items),
        items=ordered_items[start:end],
        page=page,
        page_size=page_size,
        has_more=end < len(ordered_items),
    )


def collect_paper_library_filter_options(db: Session) -> dict[str, list[str]]:
    rows = db.execute(
        select(
            ImportedLiteratureItem.category,
            ImportedLiteratureItem.publish_date,
            ImportedLiteratureItem.tags_json,
        )
        .join(ImportedDigestMembership, ImportedDigestMembership.literature_item_id == ImportedLiteratureItem.id)
        .where(ImportedDigestMembership.list_type == "digest")
    ).all()

    publish_dates: set[str] = set()
    categories: set[str] = set()
    tags: set[str] = set()

    for row in rows:
        category = str(row.category or "").strip()
        if category:
            categories.add(category)
        normalized_publish_date = normalize_publish_date(str(row.publish_date or ""))
        if normalized_publish_date:
            publish_dates.add(normalized_publish_date)
        for tag in row.tags_json or []:
            cleaned_tag = str(tag or "").strip()
            if cleaned_tag:
                tags.add(cleaned_tag)

    return {
        "available_publish_dates": order_publish_dates(publish_dates, DEFAULT_LIBRARY_SORT),
        "available_categories": sorted(categories),
        "available_tags": sorted(tags),
    }


def load_paper_library_papers(db: Session, user_id: int, filters: PaperLibraryFilters) -> list[DigestPaper]:
    statement = (
        select(ImportedLiteratureItem, ImportedDigestMembership)
        .join(ImportedDigestMembership, ImportedDigestMembership.literature_item_id == ImportedLiteratureItem.id)
        .where(ImportedDigestMembership.list_type == "digest")
        .order_by(
            ImportedLiteratureItem.publish_date.desc(),
            ImportedLiteratureItem.id.desc(),
            ImportedDigestMembership.digest_date.desc(),
        )
    )
    if filters.category:
        statement = statement.where(ImportedLiteratureItem.category == filters.category)
    if filters.query:
        statement = _apply_text_filter(db, statement, filters.query)
    if filters.publish_date and filters.publish_date != UNKNOWN_PUBLISH_DATE:
        statement = statement.where(ImportedLiteratureItem.publish_date.like(f"{filters.publish_date}%"))

    rows = _dedupe_library_rows(db.execute(statement).all())
    item_keys = [row.ImportedLiteratureItem.literature_item_key for row in rows]
    favorite_keys = _fetch_favorite_keys(db, user_id, item_keys)

    papers: list[DigestPaper] = []
    for row in rows:
        paper = build_digest_paper(row, favorite_keys)
        if filters.publish_date and paper.publish_date_day != filters.publish_date:
            continue
        if filters.tag and filters.tag not in paper.tags:
            continue
        papers.append(paper)
    return papers


def load_paper_library_index(db: Session, filters: PaperLibraryFilters) -> list[tuple[int, str]]:
    statement = (
        select(
            ImportedLiteratureItem.id,
            ImportedLiteratureItem.publish_date,
            ImportedLiteratureItem.tags_json,
        )
        .join(ImportedDigestMembership, ImportedDigestMembership.literature_item_id == ImportedLiteratureItem.id)
        .where(ImportedDigestMembership.list_type == "digest")
        .order_by(ImportedDigestMembership.digest_date.desc())
    )
    if filters.category:
        statement = statement.where(ImportedLiteratureItem.category == filters.category)
    if filters.query:
        statement = _apply_text_filter(db, statement, filters.query)
    if filters.publish_date and filters.publish_date != UNKNOWN_PUBLISH_DATE:
        statement = statement.where(ImportedLiteratureItem.publish_date.like(f"{filters.publish_date}%"))

    latest_rows = {}
    for row in db.execute(statement):
        if row.id not in latest_rows:
            latest_rows[row.id] = row

    indexed: list[tuple[int, str]] = []
    for row in latest_rows.values():
        publish_date = normalize_publish_date(str(row.publish_date or ""))
        if filters.publish_date and publish_date != filters.publish_date:
            continue
        if filters.tag and filters.tag not in (row.tags_json or []):
            continue
        indexed.append((row.id, publish_date))
    return indexed



def _can_use_materialized_stats(filters: PaperLibraryFilters) -> bool:
    return not any((filters.query, filters.category, filters.tag, filters.publish_date))


def _apply_text_filter(db: Session, statement, query: str):
    if search_index_available(db):
        return apply_full_text_filter(statement, query)
    like_value = f"%{query}%"
    return statement.where(or_(
        ImportedLiteratureItem.title_en.ilike(like_value),
        ImportedLiteratureItem.title_zh.ilike(like_value),
        ImportedLiteratureItem.summary_zh.ilike(like_value),
        ImportedLiteratureItem.abstract.ilike(like_value),
        ImportedLiteratureItem.journal.ilike(like_value),
        ImportedLiteratureItem.interest_tag.ilike(like_value),
    ))

def order_publish_dates(values, sort: str) -> list[str]:
    valid_dates: dict[str, date_type] = {}
    invalid_dates: set[str] = set()
    for value in values:
        normalized = str(value or "").strip()
        if not normalized:
            continue
        try:
            valid_dates[normalized] = date_type.fromisoformat(normalized)
        except ValueError:
            invalid_dates.add(normalized)

    ordered_valid = sorted(
        valid_dates.items(),
        key=lambda item: item[1],
        reverse=normalize_library_sort(sort) == "publish_date_desc",
    )
    return [value for value, _ in ordered_valid] + sorted(invalid_dates)


def _normalize_requested_publish_date(value: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        return ""
    return normalize_publish_date(cleaned)


def _dedupe_library_rows(rows) -> list:
    latest_by_item_id = {}
    for row in rows:
        paper_id = row.ImportedLiteratureItem.id
        if paper_id not in latest_by_item_id:
            latest_by_item_id[paper_id] = row
    return list(latest_by_item_id.values())


def _fetch_favorite_keys(db: Session, user_id: int, item_keys: list[str]) -> set[str]:
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


def _group_papers_by_publish_date(papers: list[DigestPaper]) -> dict[str, list[DigestPaper]]:
    grouped: dict[str, list[DigestPaper]] = {}
    for paper in papers:
        grouped.setdefault(paper.publish_date_day, []).append(paper)
    return grouped


def _group_paper_ids_by_publish_date(papers: list[tuple[int, str]]) -> dict[str, list[int]]:
    grouped: dict[str, list[int]] = {}
    for paper_id, publish_date in papers:
        grouped.setdefault(publish_date, []).append(paper_id)
    return grouped


def _sort_group_items(items: list[DigestPaper]) -> list[DigestPaper]:
    return sorted(items, key=_paper_priority_key)


def _paper_priority_key(item: DigestPaper) -> tuple[int, int, int, int, int]:
    flagship_rank = _flagship_journal_rank(item.journal)
    return (
        0 if flagship_rank < len(FLAGSHIP_JOURNAL_ORDER) else 1,
        flagship_rank,
        _interest_priority(item.interest_level),
        -item.interest_score,
        -item.id,
    )


def _interest_priority(level: str) -> int:
    if "非常感兴趣" in level:
        return 0
    if "感兴趣" in level:
        return 1
    if "一般" in level:
        return 2
    return 9


def _flagship_journal_rank(journal: str) -> int:
    normalized = str(journal or "").strip().lower()
    try:
        return FLAGSHIP_JOURNAL_ORDER.index(normalized)
    except ValueError:
        return len(FLAGSHIP_JOURNAL_ORDER)
