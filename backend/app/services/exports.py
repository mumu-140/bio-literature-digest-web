from __future__ import annotations

import csv
import io
from datetime import date as date_type, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ImportedDigestMembership, ImportedLiteratureItem, UserExportJobV2


def create_export_job(
    db: Session,
    *,
    requested_by_user_id: Optional[int],
    requested_by_key: str,
    kind: str,
    output_name: str,
    content_type: str,
    content_text: str,
    params: dict,
) -> UserExportJobV2:
    job = UserExportJobV2(
        requested_by_user_id=requested_by_user_id,
        requested_by_key=requested_by_key,
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


def fetch_items_for_export(db: Session, date_value: Optional[str]) -> list[ImportedLiteratureItem]:
    statement = (
        select(ImportedLiteratureItem)
        .join(ImportedDigestMembership, ImportedDigestMembership.literature_item_id == ImportedLiteratureItem.id)
        .where(ImportedDigestMembership.list_type == "digest")
    )
    if date_value:
        statement = statement.where(ImportedDigestMembership.digest_date == date_type.fromisoformat(date_value))
    return list(db.scalars(statement).unique())


def csv_from_rows(rows: list[dict[str, str]], columns: list[tuple[str, str]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=[label for _, label in columns])
    writer.writeheader()
    for row in rows:
        writer.writerow({label: row.get(source, "") for source, label in columns})
    return buffer.getvalue()


def items_to_rows(items: list[ImportedLiteratureItem]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in items:
        rows.append(
            {
                "id": str(item.id),
                "canonical_key": item.literature_item_key,
                "doi": item.doi,
                "journal": item.journal,
                "publish_date": item.publish_date,
                "category": item.category,
                "interest_level": item.interest_level,
                "interest_tag": item.interest_tag,
                "title_en": item.title_en,
                "title_zh": item.title_zh,
                "summary_zh": item.summary_zh,
                "abstract": item.abstract,
                "article_url": item.article_url,
                "tags": ", ".join(item.tags_json or []),
            }
        )
    return rows
