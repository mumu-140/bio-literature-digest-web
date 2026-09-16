from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import sqlite3
from typing import Any


@dataclass(frozen=True)
class ProducerRun:
    run_id: str
    digest_date: str
    status: str
    email_status: str
    window_start_utc: str
    window_end_utc: str
    work_dir: str
    metadata_json: dict[str, Any]
    updated_at_utc: str


@dataclass(frozen=True)
class ProducerPaperRecord:
    record_id: int
    run_id: str
    digest_date: str
    list_type: str
    unique_key: str
    journal: str
    publish_date: str
    category: str
    interest_level: str
    interest_tag: str
    title_en: str
    title_zh: str
    summary_zh: str
    abstract: str
    doi: str
    article_url: str
    tags: str
    updated_at_utc: str
    article_url_norm: str
    paper_article_url: str
    paper_doi: str
    paper_journal: str
    row_json: dict[str, Any]


@dataclass(frozen=True)
class ProducerSnapshot:
    runs: list[ProducerRun]
    records_by_run: dict[str, list[ProducerPaperRecord]]


def _json_loads(raw_value: str | None) -> dict[str, Any]:
    if not raw_value:
        return {}
    try:
        loaded = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _read_runs(connection: sqlite3.Connection) -> list[ProducerRun]:
    rows = connection.execute(
        """
        SELECT run_id, archive_date, status, email_status, window_start_utc, window_end_utc, work_dir, metadata_json, updated_at_utc
        FROM runs
        ORDER BY archive_date DESC, updated_at_utc DESC, run_id DESC
        """
    ).fetchall()
    return [
        ProducerRun(
            run_id=str(row["run_id"] or "").strip(),
            digest_date=str(row["archive_date"] or "").strip(),
            status=str(row["status"] or "").strip(),
            email_status=str(row["email_status"] or "").strip(),
            window_start_utc=str(row["window_start_utc"] or "").strip(),
            window_end_utc=str(row["window_end_utc"] or "").strip(),
            work_dir=str(row["work_dir"] or "").strip(),
            metadata_json=_json_loads(row["metadata_json"]),
            updated_at_utc=str(row["updated_at_utc"] or "").strip(),
        )
        for row in rows
    ]


def _read_records(connection: sqlite3.Connection, run_ids: list[str]) -> dict[str, list[ProducerPaperRecord]]:
    if not run_ids:
        return {}
    placeholders = ",".join("?" for _ in run_ids)
    rows = connection.execute(
        f"""
        SELECT
          pr.id AS record_id,
          pr.run_id,
          pr.archive_date,
          pr.dataset,
          pr.journal,
          pr.publish_date,
          pr.category,
          pr.interest_level,
          pr.interest_tag,
          pr.title_en,
          pr.title_zh,
          pr.summary_zh,
          pr.abstract,
          pr.doi,
          pr.article_url,
          pr.tags,
          pr.updated_at_utc,
          pr.row_json,
          p.unique_key,
          p.article_url_norm,
          p.article_url AS paper_article_url,
          p.doi AS paper_doi,
          p.journal AS paper_journal
        FROM paper_records AS pr
        JOIN papers AS p ON p.id = pr.paper_id
        WHERE pr.run_id IN ({placeholders})
        ORDER BY pr.archive_date ASC, pr.dataset ASC, pr.id ASC
        """,
        run_ids,
    ).fetchall()
    grouped: dict[str, list[ProducerPaperRecord]] = {run_id: [] for run_id in run_ids}
    for row in rows:
        record = ProducerPaperRecord(
            record_id=int(row["record_id"]),
            run_id=str(row["run_id"] or "").strip(),
            digest_date=str(row["archive_date"] or "").strip(),
            list_type=str(row["dataset"] or "digest").strip() or "digest",
            unique_key=str(row["unique_key"] or "").strip(),
            journal=str(row["journal"] or "").strip(),
            publish_date=str(row["publish_date"] or "").strip(),
            category=str(row["category"] or "").strip(),
            interest_level=str(row["interest_level"] or "").strip(),
            interest_tag=str(row["interest_tag"] or "").strip(),
            title_en=str(row["title_en"] or "").strip(),
            title_zh=str(row["title_zh"] or "").strip(),
            summary_zh=str(row["summary_zh"] or "").strip(),
            abstract=str(row["abstract"] or "").strip(),
            doi=str(row["doi"] or "").strip(),
            article_url=str(row["article_url"] or "").strip(),
            tags=str(row["tags"] or "").strip(),
            updated_at_utc=str(row["updated_at_utc"] or "").strip(),
            article_url_norm=str(row["article_url_norm"] or "").strip(),
            paper_article_url=str(row["paper_article_url"] or "").strip(),
            paper_doi=str(row["paper_doi"] or "").strip(),
            paper_journal=str(row["paper_journal"] or "").strip(),
            row_json=_json_loads(row["row_json"]),
        )
        grouped.setdefault(record.run_id, []).append(record)
    return grouped


def load_snapshot(producer_db_path: Path) -> ProducerSnapshot:
    if not producer_db_path.exists():
        return ProducerSnapshot(runs=[], records_by_run={})
    with sqlite3.connect(str(producer_db_path)) as connection:
        connection.row_factory = sqlite3.Row
        runs = _read_runs(connection)
        records_by_run = _read_records(connection, [run.run_id for run in runs if run.run_id])
    return ProducerSnapshot(runs=runs, records_by_run=records_by_run)
