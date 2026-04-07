from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from datetime import date, datetime
from typing import Optional

from sqlalchemy import and_, delete, func, select
from sqlalchemy.orm import Session, joinedload

from ..models import AnalyticsEdge, AnalyticsNode, AnalyticsSnapshot, Favorite, Paper, PaperDailyEntry

INTEREST_THRESHOLD = 3
CNS_JOURNALS = ("Cell", "Nature", "Science")


def normalize_term(term: str) -> str:
    return term.strip().lower().replace("_", " ")


def month_bounds(month: str) -> tuple[date, date]:
    year, month_part = [int(part) for part in month.split("-")]
    start = date(year, month_part, 1)
    if month_part == 12:
        return start, date(year + 1, 1, 1)
    return start, date(year, month_part + 1, 1)


def extract_terms(paper: Paper) -> list[str]:
    terms = [normalize_term(tag) for tag in (paper.tags_json or []) if normalize_term(tag)]
    interest_tag = normalize_term(paper.interest_tag)
    if interest_tag:
        terms.append(interest_tag)
    deduped: list[str] = []
    for term in terms:
        if term and term not in deduped:
            deduped.append(term)
    return deduped


def week_label(date_value: str) -> str:
    try:
        parsed = datetime.fromisoformat(date_value.replace("Z", "+00:00"))
        return f"W{parsed.isocalendar().week}"
    except ValueError:
        return "unknown"


def build_network(papers: Iterable[Paper]) -> tuple[dict[str, int], Counter[tuple[str, str]]]:
    node_counter: dict[str, int] = {}
    edge_counter: Counter[tuple[str, str]] = Counter()
    for paper in papers:
        terms = extract_terms(paper)
        for term in terms:
            node_counter[term] = node_counter.get(term, 0) + 1
        for index, left in enumerate(terms):
            for right in terms[index + 1 :]:
                pair = tuple(sorted((left, right)))
                edge_counter[pair] += 1
    return node_counter, edge_counter


def fetch_monthly_papers(db: Session, month: str) -> list[Paper]:
    start, end = month_bounds(month)
    statement = (
        select(Paper)
        .join(PaperDailyEntry, PaperDailyEntry.paper_id == Paper.id)
        .where(
            and_(
                PaperDailyEntry.digest_date >= start,
                PaperDailyEntry.digest_date < end,
                Paper.interest_score >= INTEREST_THRESHOLD,
            )
        )
        .order_by(PaperDailyEntry.digest_date.asc())
    )
    return list(db.scalars(statement).unique())


def fetch_user_favorite_papers(db: Session, user_id: int, month: str) -> list[Paper]:
    start, end = month_bounds(month)
    statement = (
        select(Paper)
        .join(Favorite, Favorite.paper_id == Paper.id)
        .join(PaperDailyEntry, PaperDailyEntry.paper_id == Paper.id)
        .where(
            and_(
                Favorite.user_id == user_id,
                PaperDailyEntry.digest_date >= start,
                PaperDailyEntry.digest_date < end,
            )
        )
        .order_by(PaperDailyEntry.digest_date.asc())
    )
    return list(db.scalars(statement).unique())


def compute_series_from_papers(papers: Iterable[Paper]) -> list[dict[str, int | str]]:
    counter: Counter[str] = Counter()
    for paper in papers:
        counter[week_label(paper.publish_date)] += 1
    return [{"label": label, "value": counter[label]} for label in sorted(counter)]


def persist_snapshot(
    db: Session,
    *,
    scope_type: str,
    period: str,
    month: str,
    snapshot_kind: str,
    papers: list[Paper],
    user_id: Optional[int] = None,
) -> AnalyticsSnapshot:
    snapshot = db.scalar(
        select(AnalyticsSnapshot).where(
            AnalyticsSnapshot.scope_type == scope_type,
            AnalyticsSnapshot.user_id == user_id,
            AnalyticsSnapshot.period == period,
            AnalyticsSnapshot.month == month,
            AnalyticsSnapshot.snapshot_kind == snapshot_kind,
        )
    )
    if snapshot is None:
        snapshot = AnalyticsSnapshot(
            scope_type=scope_type,
            user_id=user_id,
            period=period,
            month=month,
            snapshot_kind=snapshot_kind,
        )
        db.add(snapshot)
        db.flush()
    else:
        db.execute(delete(AnalyticsNode).where(AnalyticsNode.snapshot_id == snapshot.id))
        db.execute(delete(AnalyticsEdge).where(AnalyticsEdge.snapshot_id == snapshot.id))

    node_counter, edge_counter = build_network(papers)
    summary = {
        "top_categories": Counter(paper.category for paper in papers).most_common(10),
        "top_journals": Counter(paper.journal for paper in papers).most_common(10),
    }
    snapshot.generated_at = datetime.utcnow()
    snapshot.total_papers = len(papers)
    snapshot.payload_json = {
        "series": compute_series_from_papers(papers),
        "summary": summary,
    }
    db.flush()

    for key, weight in sorted(node_counter.items()):
        db.add(AnalyticsNode(snapshot_id=snapshot.id, node_key=key, label=key, weight=weight))
    for (source, target), weight in sorted(edge_counter.items()):
        db.add(AnalyticsEdge(snapshot_id=snapshot.id, source_key=source, target_key=target, weight=weight))

    db.commit()
    db.refresh(snapshot)
    snapshot = db.scalar(
        select(AnalyticsSnapshot)
        .options(joinedload(AnalyticsSnapshot.nodes), joinedload(AnalyticsSnapshot.edges))
        .where(AnalyticsSnapshot.id == snapshot.id)
    )
    return snapshot


def build_global_snapshot(db: Session, period: str, month: str) -> AnalyticsSnapshot:
    return persist_snapshot(
        db,
        scope_type="global",
        period=period,
        month=month,
        snapshot_kind="network",
        papers=fetch_monthly_papers(db, month),
    )


def build_user_snapshot(db: Session, user_id: int, period: str, month: str) -> AnalyticsSnapshot:
    return persist_snapshot(
        db,
        scope_type="user",
        user_id=user_id,
        period=period,
        month=month,
        snapshot_kind="favorites",
        papers=fetch_user_favorite_papers(db, user_id, month),
    )


def build_cns_trends(db: Session, months: int) -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []
    today = datetime.utcnow()
    for offset in range(months - 1, -1, -1):
        year = today.year
        month = today.month - offset
        while month <= 0:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        month_key = f"{year:04d}-{month:02d}"
        start, end = month_bounds(month_key)
        for journal in CNS_JOURNALS:
            count = db.scalar(
                select(func.count(Paper.id))
                .join(PaperDailyEntry, PaperDailyEntry.paper_id == Paper.id)
                .where(
                    PaperDailyEntry.digest_date >= start,
                    PaperDailyEntry.digest_date < end,
                    Paper.journal == journal,
                )
            )
            rows.append({"label": month_key, "value": int(count or 0), "journal": journal})
    return rows
