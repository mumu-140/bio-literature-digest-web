from __future__ import annotations

import csv
import io
from datetime import date as date_type, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ExportJob, Favorite, Paper, PaperDailyEntry, User


def create_export_job(
    db: Session,
    *,
    requested_by: User,
    kind: str,
    output_name: str,
    content_type: str,
    content_text: str,
    params: dict,
) -> ExportJob:
    job = ExportJob(
        requested_by=requested_by.id,
        kind=kind,
        status="completed",
        output_name=output_name,
        content_type=content_type,
        content_text=content_text,
        params_json=params,
        finished_at=datetime.utcnow(),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def fetch_papers_for_export(db: Session, date_value: Optional[str]) -> list[Paper]:
    statement = select(Paper).join(PaperDailyEntry, PaperDailyEntry.paper_id == Paper.id)
    if date_value:
        statement = statement.where(PaperDailyEntry.digest_date == date_type.fromisoformat(date_value))
    return list(db.scalars(statement).unique())


def fetch_favorites_for_export(db: Session, user_id: int) -> list[Favorite]:
    return list(db.scalars(select(Favorite).where(Favorite.user_id == user_id).order_by(Favorite.favorited_at.desc())))


def csv_from_rows(rows: list[dict[str, str]], columns: list[tuple[str, str]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=[label for _, label in columns])
    writer.writeheader()
    for row in rows:
        writer.writerow({label: row.get(source, "") for source, label in columns})
    return buffer.getvalue()


def papers_to_rows(papers: list[Paper]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for paper in papers:
        rows.append(
            {
                "id": str(paper.id),
                "doi": paper.doi,
                "journal": paper.journal,
                "publish_date": paper.publish_date,
                "category": paper.category,
                "interest_level": paper.interest_level,
                "interest_tag": paper.interest_tag,
                "title_en": paper.title_en,
                "title_zh": paper.title_zh,
                "summary_zh": paper.summary_zh,
                "abstract": paper.abstract,
                "article_url": paper.article_url,
                "tags": ", ".join(paper.tags_json or []),
            }
        )
    return rows
