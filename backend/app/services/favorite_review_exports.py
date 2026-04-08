from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from ..config import get_settings
from ..models import Favorite, Paper, PaperDailyEntry, User

REVIEW_DECISIONS = ["keep", "review", "reject"]


def _load_yaml_file(path: str | Path) -> Any:
    path_obj = Path(path)
    try:
        import yaml  # type: ignore

        with path_obj.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except ModuleNotFoundError:
        command = [
            "ruby",
            "-ryaml",
            "-rjson",
            "-e",
            "print JSON.dump(YAML.load_file(ARGV[0]))",
            str(path_obj),
        ]
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        return json.loads(completed.stdout)


def get_review_rules() -> dict[str, Any]:
    settings = get_settings()
    loaded = _load_yaml_file(settings.producer_rules_path) or {}
    return loaded if isinstance(loaded, dict) else {}


def get_review_options() -> dict[str, list[str]]:
    rules = get_review_rules()
    interest_profile = rules.get("interest_profile", {})
    interest_taxonomy = rules.get("interest_tag_taxonomy", {})
    categories = rules.get("categories", {})
    interest_levels = [
        str(item.get("label", "")).strip()
        for item in interest_profile.get("levels", [])
        if isinstance(item, dict) and str(item.get("label", "")).strip()
    ]
    interest_tags = [str(item).strip() for item in interest_taxonomy.get("labels", []) if str(item).strip()]
    if isinstance(categories, dict):
        review_final_categories = [str(item).strip() for item in categories.keys() if str(item).strip()]
    else:
        review_final_categories = [
            str(item.get("id", "")).strip()
            for item in categories
            if isinstance(item, dict) and str(item.get("id", "")).strip()
        ]
    return {
        "interest_levels": interest_levels,
        "interest_tags": interest_tags,
        "review_final_decisions": list(REVIEW_DECISIONS),
        "review_final_categories": review_final_categories,
    }


def normalize_review_field(value: str | None) -> str:
    return str(value or "").strip()


def normalize_favorite_review_payload(
    favorite: Any,
    *,
    review_interest_level: str,
    review_interest_tag: str,
    review_final_decision: str,
    review_final_category: str,
    reviewer_notes: str,
) -> dict[str, str]:
    base_item = getattr(favorite, "paper", None) or getattr(favorite, "item", None)
    base_interest_level = normalize_review_field(getattr(base_item, "interest_level", ""))
    base_interest_tag = normalize_review_field(getattr(base_item, "interest_tag", ""))
    base_category = normalize_review_field(getattr(base_item, "category", ""))
    normalized = {
        "review_interest_level": normalize_review_field(review_interest_level),
        "review_interest_tag": normalize_review_field(review_interest_tag),
        "review_final_decision": normalize_review_field(review_final_decision),
        "review_final_category": normalize_review_field(review_final_category),
        "reviewer_notes": normalize_review_field(reviewer_notes),
    }
    if normalized["review_interest_level"] == base_interest_level:
        normalized["review_interest_level"] = ""
    if normalized["review_interest_tag"] == base_interest_tag:
        normalized["review_interest_tag"] = ""
    if normalized["review_final_category"] == base_category:
        normalized["review_final_category"] = ""
    return normalized


def favorite_has_review_update(favorite: Favorite) -> bool:
    return any(
        [
            normalize_review_field(favorite.review_interest_level),
            normalize_review_field(favorite.review_interest_tag),
            normalize_review_field(favorite.review_final_decision),
            normalize_review_field(favorite.review_final_category),
            normalize_review_field(favorite.reviewer_notes),
        ]
    )


def user_review_weight(user: User) -> int:
    if user.user_group == "outsider":
        return 1
    if user.role == "admin":
        return 3
    return 2


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip())
    return cleaned.strip("._-") or "user"


def _review_key(favorite: Favorite) -> str:
    if favorite.paper.doi:
        return f"doi:{favorite.paper.doi.strip().lower()}"
    if favorite.paper.canonical_key:
        return favorite.paper.canonical_key
    return f"paper:{favorite.paper_id}"


def _latest_daily_entry(paper: Paper) -> PaperDailyEntry | None:
    entries = list(paper.daily_entries or [])
    if not entries:
        return None
    return max(entries, key=lambda entry: (entry.digest_date, entry.created_at, entry.id))


def _favorite_sort_timestamp(favorite: Favorite) -> datetime:
    return favorite.review_updated_at or favorite.favorited_at


def _build_review_record(favorite: Favorite) -> dict[str, Any]:
    latest_entry = _latest_daily_entry(favorite.paper)
    raw_record = latest_entry.raw_record_json if latest_entry else {}
    publication_stage = ""
    if latest_entry is not None:
        publication_stage = latest_entry.publication_stage
    publication_stage = str(publication_stage or raw_record.get("publication_stage") or "journal")
    tags = favorite.paper.tags_json or raw_record.get("tags") or []
    if not isinstance(tags, list):
        tags = [str(tags)]
    return {
        "source_id": str(raw_record.get("source_id") or favorite.paper.extra_json.get("source_id") or favorite.paper.canonical_key),
        "journal": favorite.paper.journal,
        "publish_date": favorite.paper.publish_date,
        "publication_stage": publication_stage,
        "category": favorite.paper.category,
        "interest_level": favorite.review_interest_level or favorite.paper.interest_level,
        "interest_tag": favorite.review_interest_tag or favorite.paper.interest_tag,
        "review_interest_level": favorite.review_interest_level,
        "review_interest_tag": favorite.review_interest_tag,
        "title_en": favorite.paper.title_en,
        "title_zh": favorite.paper.title_zh,
        "summary_zh": favorite.paper.summary_zh,
        "abstract": favorite.paper.abstract,
        "doi": favorite.paper.doi,
        "article_url": favorite.paper.article_url,
        "tags": tags,
        "llm_decision": str(raw_record.get("llm_decision") or raw_record.get("final_decision") or ""),
        "llm_confidence": str(raw_record.get("llm_confidence") or ""),
        "llm_reason": str(raw_record.get("llm_reason") or raw_record.get("decision_reason") or ""),
        "review_final_decision": favorite.review_final_decision,
        "review_final_category": favorite.review_final_category,
        "reviewer_notes": favorite.reviewer_notes,
        "_paper_id": favorite.paper_id,
        "_favorite_id": favorite.id,
        "_favorite_user_id": favorite.user_id,
        "_favorite_email": favorite.user.email,
        "_favorite_name": favorite.user.name,
        "_favorite_role": favorite.user.role,
        "_favorite_group": favorite.user.user_group,
        "_review_weight": user_review_weight(favorite.user),
        "_review_updated_at": (_favorite_sort_timestamp(favorite).astimezone(timezone.utc).replace(microsecond=0).isoformat()),
        "_review_key": _review_key(favorite),
    }


def _dedupe_records_by_latest(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_by_key: dict[str, dict[str, Any]] = {}
    for record in records:
        key = str(record.get("_review_key") or "")
        current = latest_by_key.get(key)
        if current is None or str(record.get("_review_updated_at") or "") >= str(current.get("_review_updated_at") or ""):
            latest_by_key[key] = record
    return sorted(latest_by_key.values(), key=lambda item: str(item.get("_review_updated_at") or ""), reverse=True)


def _review_source_statement():
    return (
        select(Favorite)
        .options(
            joinedload(Favorite.user),
            joinedload(Favorite.paper).joinedload(Paper.daily_entries),
        )
        .where(
            or_(
                Favorite.review_interest_level != "",
                Favorite.review_interest_tag != "",
                Favorite.review_final_decision != "",
                Favorite.review_final_category != "",
                Favorite.reviewer_notes != "",
                Favorite.review_updated_at.is_not(None),
            )
        )
    )


def fetch_modified_favorites(db: Session) -> list[Favorite]:
    statement = _review_source_statement()
    favorites = list(db.execute(statement).unique().scalars())
    return sorted(favorites, key=_favorite_sort_timestamp, reverse=True)


def build_user_review_records(db: Session) -> dict[int, list[dict[str, Any]]]:
    favorites = fetch_modified_favorites(db)
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for favorite in favorites:
        grouped[favorite.user_id].append(_build_review_record(favorite))
    return {user_id: _dedupe_records_by_latest(records) for user_id, records in grouped.items()}


def _weighted_choice(records: list[dict[str, Any]], field: str, fallback: str = "") -> str:
    scores: dict[str, int] = defaultdict(int)
    latest_by_value: dict[str, str] = {}
    for record in records:
        value = str(record.get(field) or "").strip()
        if not value:
            continue
        scores[value] += int(record.get("_review_weight") or 0)
        latest_by_value[value] = max(str(record.get("_review_updated_at") or ""), latest_by_value.get(value, ""))
    if not scores:
        return fallback
    return sorted(scores, key=lambda value: (scores[value], latest_by_value.get(value, ""), value), reverse=True)[0]


def build_weighted_review_records(db: Session) -> list[dict[str, Any]]:
    favorites = fetch_modified_favorites(db)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for favorite in favorites:
        record = _build_review_record(favorite)
        grouped[str(record["_review_key"])].append(record)
    aggregated: list[dict[str, Any]] = []
    for key, records in grouped.items():
        ordered = sorted(records, key=lambda item: str(item.get("_review_updated_at") or ""), reverse=True)
        latest = dict(ordered[0])
        contributors = ", ".join(
            f'{record["_favorite_name"]}({record["_review_weight"]})'
            for record in sorted(
                ordered,
                key=lambda item: (int(item.get("_review_weight") or 0), str(item.get("_review_updated_at") or "")),
                reverse=True,
            )
        )
        note_lines: list[str] = [
            f'weighted_total={sum(int(record.get("_review_weight") or 0) for record in ordered)}; contributors={contributors}'
        ]
        for record in ordered:
            note_text = normalize_review_field(str(record.get("reviewer_notes") or ""))
            vote_parts = [
                part
                for part in [
                    f'interest_level={record.get("interest_level")}' if record.get("review_interest_level") else "",
                    f'interest_tag={record.get("interest_tag")}' if record.get("review_interest_tag") else "",
                    f'final_decision={record.get("review_final_decision")}' if record.get("review_final_decision") else "",
                    f'final_category={record.get("review_final_category")}' if record.get("review_final_category") else "",
                ]
                if part
            ]
            detail = "; ".join(vote_parts)
            suffix = f" | {note_text}" if note_text else ""
            if detail or note_text:
                note_lines.append(
                    f'[{record["_review_weight"]}] {record["_favorite_name"]} {record["_review_updated_at"]}: {detail}{suffix}'.strip()
                )
        latest["interest_level"] = _weighted_choice(ordered, "review_interest_level", fallback=str(latest.get("interest_level") or ""))
        latest["interest_tag"] = _weighted_choice(ordered, "review_interest_tag", fallback=str(latest.get("interest_tag") or ""))
        latest["review_final_decision"] = _weighted_choice(ordered, "review_final_decision", fallback="")
        latest["review_final_category"] = _weighted_choice(ordered, "review_final_category", fallback="")
        latest["reviewer_notes"] = "\n".join(note_lines)
        latest["_review_key"] = key
        latest["_review_updated_at"] = max(str(record.get("_review_updated_at") or "") for record in ordered)
        aggregated.append(latest)
    return _dedupe_records_by_latest(aggregated)


def _json_ready(record: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in record.items():
        if key.startswith("_"):
            continue
        normalized[key] = value
    return normalized


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(_json_ready(record), ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def _run_review_export(input_path: Path, html_path: Path, csv_path: Path, xlsx_path: Path) -> None:
    settings = get_settings()
    command = [
        sys.executable,
        str(Path(settings.producer_root) / "scripts" / "export_digest.py"),
        "--input",
        str(input_path),
        "--rules",
        str(settings.producer_rules_path),
        "--html-output",
        str(html_path),
        "--csv-output",
        str(csv_path),
        "--xlsx-output",
        str(xlsx_path),
        "--template",
        str(settings.producer_review_template_path),
        "--schema-key",
        "daily_review_schema",
    ]
    subprocess.run(command, check=True)


def _export_record_set(records: list[dict[str, Any]], target_dir: Path, stem: str) -> dict[str, str]:
    target_dir.mkdir(parents=True, exist_ok=True)
    html_path = target_dir / f"{stem}.html"
    csv_path = target_dir / f"{stem}.csv"
    xlsx_path = target_dir / f"{stem}.xlsx"
    with tempfile.TemporaryDirectory(prefix="favorite-review-export-") as tmpdir:
        input_path = Path(tmpdir) / f"{stem}.jsonl"
        _write_jsonl(input_path, records)
        _run_review_export(input_path, html_path, csv_path, xlsx_path)
    return {
        "html": str(html_path),
        "csv": str(csv_path),
        "xlsx": str(xlsx_path),
    }


def _relative_manifest_paths(paths: dict[str, str], *, review_root: Path) -> dict[str, str]:
    return {key: str(Path(value).resolve().relative_to(review_root.resolve())) for key, value in paths.items()}


def export_favorite_review_tables(db: Session, *, generated_at: datetime | None = None) -> dict[str, Any]:
    settings = get_settings()
    generated = (generated_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    stamp = generated.strftime("%Y-%m-%d")
    review_root = Path(settings.review_export_dir)
    current_root = review_root / "current"
    archive_root = review_root / "archive" / stamp
    users = list(db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.id.asc())))
    records_by_user = build_user_review_records(db)
    per_user_outputs: list[dict[str, Any]] = []
    for user in users:
        records = records_by_user.get(user.id, [])
        user_dir_name = f"{user.id:03d}-{_safe_segment(user.email)}"
        current_paths = _export_record_set(records, current_root / "users" / user_dir_name, "favorite-review-current")
        archive_paths = _export_record_set(records, archive_root / "users" / user_dir_name, f"favorite-review-{stamp}")
        per_user_outputs.append(
            {
                "user_id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "user_group": user.user_group,
                "record_count": len(records),
                "current": _relative_manifest_paths(current_paths, review_root=review_root),
                "archive": _relative_manifest_paths(archive_paths, review_root=review_root),
            }
        )
    weighted_records = build_weighted_review_records(db)
    aggregate_current = _export_record_set(weighted_records, current_root / "aggregate", "weighted-favorite-review-current")
    aggregate_archive = _export_record_set(weighted_records, archive_root / "aggregate", f"weighted-favorite-review-{stamp}")
    manifest = {
        "generated_at": generated.replace(microsecond=0).isoformat(),
        "review_root": ".",
        "per_user": per_user_outputs,
        "aggregate": {
            "record_count": len(weighted_records),
            "current": _relative_manifest_paths(aggregate_current, review_root=review_root),
            "archive": _relative_manifest_paths(aggregate_archive, review_root=review_root),
        },
    }
    manifest_path = current_root / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    archive_manifest_path = archive_root / "manifest.json"
    archive_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    archive_manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
