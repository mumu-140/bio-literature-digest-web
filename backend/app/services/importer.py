from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from datetime import date as date_type, datetime, timedelta
from pathlib import Path
from typing import Optional, Union
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import DigestRun, Favorite, Paper, PaperDailyEntry, PaperPush

REQUIRED_COLUMNS = {
    "journal",
    "publish_date",
    "category",
    "interest_level",
    "interest_tag",
    "title_en",
    "title_zh",
    "summary_zh",
    "abstract",
    "doi",
    "article_url",
}

INTEREST_SCORES = {
    "仅保留": 1,
    "非常一般": 2,
    "一般": 3,
    "感兴趣": 4,
    "非常感兴趣": 5,
}


def canonical_key_from_row(row: dict[str, str]) -> str:
    doi = (row.get("doi") or "").strip().lower()
    if doi:
        return f"doi:{doi}"
    title = (row.get("title_en") or "").strip().lower()
    journal = (row.get("journal") or "").strip().lower()
    return f"title:{journal}:{title}"


def parse_tags(raw_value: Optional[Union[str, list[str]]]) -> list[str]:
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    if not raw_value:
        return []
    return [item.strip() for item in str(raw_value).split(",") if item.strip()]


def resolve_digest_date(metadata: dict, run_dir: Path) -> datetime.date:
    settings = get_settings()
    finished_at = str(metadata.get("finished_at_utc") or "").strip()
    if finished_at:
        finished_dt = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
        return finished_dt.astimezone(ZoneInfo(settings.cst_timezone)).date()
    try:
        return datetime.strptime(run_dir.name, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("Unable to resolve digest date from metadata or run directory name") from exc


def load_digest_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - fieldnames
        if missing:
            raise ValueError(f"digest.csv is missing required columns: {', '.join(sorted(missing))}")
        return [dict(row) for row in reader]


def validate_artifacts(run_dir: Path) -> tuple[dict, list[dict[str, str]]]:
    metadata_path = run_dir / "run_metadata.json"
    digest_csv_path = run_dir / "digest.csv"
    if not metadata_path.exists():
        raise FileNotFoundError(f"Missing run metadata: {metadata_path}")
    if not digest_csv_path.exists():
        raise FileNotFoundError(f"Missing digest CSV: {digest_csv_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    status = metadata.get("status")
    if status != "success":
        raise ValueError(f"run_metadata.json status must be success, got {status!r}")
    rows = load_digest_rows(digest_csv_path)
    return metadata, rows


def purge_expired_digest_data(db: Session, *, digest_date: date_type, retention_days: int) -> None:
    cutoff = digest_date - timedelta(days=max(retention_days - 1, 0))
    favorited_paper_ids = select(Favorite.paper_id)
    old_entry_ids = db.scalars(
        select(PaperDailyEntry.id).where(
            PaperDailyEntry.digest_date < cutoff,
            ~PaperDailyEntry.paper_id.in_(favorited_paper_ids),
        )
    ).all()
    if old_entry_ids:
        db.execute(delete(PaperDailyEntry).where(PaperDailyEntry.id.in_(old_entry_ids)))

    remaining_run_ids = select(PaperDailyEntry.digest_run_id)
    old_run_ids = db.scalars(
        select(DigestRun.id).where(
            DigestRun.digest_date < cutoff,
            ~DigestRun.id.in_(remaining_run_ids),
        )
    ).all()
    if old_run_ids:
        db.execute(delete(DigestRun).where(DigestRun.id.in_(old_run_ids)))

    paper_ids_with_entries = select(PaperDailyEntry.paper_id)
    paper_ids_with_pushes = select(PaperPush.paper_id)
    orphan_paper_ids = db.scalars(
        select(Paper.id).where(
            ~Paper.id.in_(paper_ids_with_entries),
            ~Paper.id.in_(favorited_paper_ids),
            ~Paper.id.in_(paper_ids_with_pushes),
        )
    ).all()
    if orphan_paper_ids:
        db.execute(delete(Paper).where(Paper.id.in_(orphan_paper_ids)))


def import_digest_run(db: Session, run_dir: str | Path) -> tuple[DigestRun, int]:
    run_dir_path = Path(run_dir).resolve()
    metadata, rows = validate_artifacts(run_dir_path)
    digest_date = resolve_digest_date(metadata, run_dir_path)

    existing_run = db.scalar(select(DigestRun).where(DigestRun.digest_date == digest_date))
    if existing_run:
        db.execute(delete(PaperDailyEntry).where(PaperDailyEntry.digest_run_id == existing_run.id))
        digest_run = existing_run
    else:
        digest_run = DigestRun(digest_date=digest_date, work_dir=str(run_dir_path))
        db.add(digest_run)
        db.flush()

    digest_run.work_dir = str(run_dir_path)
    digest_run.status = str(metadata.get("status") or "success")
    digest_run.email_status = str(metadata.get("email_status") or "not_attempted")
    digest_run.window_start_utc = str(metadata.get("window", {}).get("start_utc") or "")
    digest_run.window_end_utc = str(metadata.get("window", {}).get("end_utc") or "")
    digest_run.metadata_json = metadata
    digest_run.imported_at = datetime.utcnow()

    imported = 0
    for index, row in enumerate(rows, start=1):
        canonical_key = canonical_key_from_row(row)
        paper = db.scalar(select(Paper).where(Paper.canonical_key == canonical_key))
        if paper is None:
            paper = Paper(canonical_key=canonical_key)
            db.add(paper)
            db.flush()
        paper.doi = (row.get("doi") or "").strip().lower()
        paper.journal = (row.get("journal") or "").strip()
        paper.category = (row.get("category") or "other").strip()
        paper.publish_date = (row.get("publish_date") or "").strip()
        paper.interest_level = (row.get("interest_level") or "一般").strip()
        paper.interest_score = INTEREST_SCORES.get(paper.interest_level, 3)
        paper.interest_tag = (row.get("interest_tag") or "其他").strip()
        paper.title_en = (row.get("title_en") or "").strip()
        paper.title_zh = (row.get("title_zh") or "").strip()
        paper.summary_zh = (row.get("summary_zh") or "").strip()
        paper.abstract = (row.get("abstract") or "").strip()
        paper.article_url = (row.get("article_url") or "").strip()
        paper.tags_json = parse_tags(row.get("tags"))
        paper.extra_json = {key: value for key, value in row.items() if key not in REQUIRED_COLUMNS and key != "tags"}

        entry = PaperDailyEntry(
            digest_run_id=digest_run.id,
            paper_id=paper.id,
            digest_date=digest_date,
            publication_stage=(row.get("publication_stage") or "journal").strip() or "journal",
            row_index=index,
            raw_record_json=row,
        )
        db.add(entry)
        imported += 1

    db.flush()
    purge_expired_digest_data(db, digest_date=digest_date, retention_days=get_settings().data_retention_days)
    db.commit()
    db.refresh(digest_run)
    return digest_run, imported


def iter_run_directories(root: Path) -> Iterable[Path]:
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "run_metadata.json").exists() and (child / "digest.csv").exists():
            yield child
