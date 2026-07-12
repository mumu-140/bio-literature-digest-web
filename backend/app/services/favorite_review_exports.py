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
from ..models import ImportedDigestMembership, ImportedLiteratureItem, User, UserManualReview

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
    base_item = getattr(favorite, "paper", None) or getattr(favorite, "item", None) or favorite
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


def user_review_weight(user: User) -> int:
    if user.user_group == "outsider":
        return 1
    if user.role == "admin":
        return 3
    return 2


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip())
    return cleaned.strip("._-") or "user"


def _review_key(review: UserManualReview) -> str:
    if review.literature_item_key:
        return review.literature_item_key
    if review.literature_item and review.literature_item.doi:
        return f"doi:{review.literature_item.doi.strip().lower()}"
    return f"review:{review.id}"


def _latest_membership(item: ImportedLiteratureItem | None) -> ImportedDigestMembership | None:
    entries = list((item.memberships if item is not None else []) or [])
    if not entries:
        return None
    list_type_rank = {"daily_review": 0, "digest": 1}
    return sorted(
        entries,
        key=lambda entry: (
            entry.digest_date,
            -list_type_rank.get(entry.list_type, 99),
            -entry.row_index,
            entry.id,
        ),
        reverse=True,
    )[0]


def _review_sort_timestamp(review: UserManualReview) -> datetime:
    return review.review_updated_at or review.updated_at or review.created_at


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.replace(microsecond=0).isoformat()


def _build_review_record(review: UserManualReview) -> dict[str, Any]:
    item = review.literature_item
    latest_entry = _latest_membership(item)
    raw_record = latest_entry.source_record_json if latest_entry else {}
    publication_stage = str(
        (latest_entry.publication_stage if latest_entry is not None else "")
        or raw_record.get("publication_stage")
        or (item.publication_stage if item is not None else "")
        or "journal"
    )
    tags = list((item.tags_json if item is not None else []) or raw_record.get("tags") or [])
    if not isinstance(tags, list):
        tags = [str(tags)]
    return {
        "source_id": str(
            raw_record.get("source_id")
            or (item.source_id if item is not None else "")
            or (item.literature_item_key if item is not None else review.literature_item_key)
        ),
        "journal": item.journal if item is not None else "",
        "publish_date": item.publish_date if item is not None else "",
        "publication_stage": publication_stage,
        "category": item.category if item is not None else "",
        "interest_level": review.review_interest_level or (item.interest_level if item is not None else ""),
        "interest_tag": review.review_interest_tag or (item.interest_tag if item is not None else ""),
        "review_interest_level": review.review_interest_level,
        "review_interest_tag": review.review_interest_tag,
        "title_en": item.title_en if item is not None else "",
        "title_zh": item.title_zh if item is not None else "",
        "summary_zh": item.summary_zh if item is not None else "",
        "abstract": item.abstract if item is not None else "",
        "doi": item.doi if item is not None else "",
        "article_url": item.article_url if item is not None else "",
        "tags": tags,
        "llm_decision": str(
            raw_record.get("llm_decision")
            or raw_record.get("final_decision")
            or (latest_entry.decision if latest_entry else "")
        ),
        "llm_confidence": str(raw_record.get("llm_confidence") or ""),
        "llm_reason": str(raw_record.get("llm_reason") or raw_record.get("decision_reason") or ""),
        "review_final_decision": review.review_final_decision,
        "review_final_category": review.review_final_category,
        "reviewer_notes": review.reviewer_notes,
        "_literature_item_key": review.literature_item_key,
        "_review_id": review.id,
        "_review_user_id": review.user_id,
        "_review_email": review.user.email,
        "_review_name": review.user.name,
        "_review_role": review.user.role,
        "_review_group": review.user.user_group,
        "_review_weight": user_review_weight(review.user),
        "_review_updated_at": _iso_utc(_review_sort_timestamp(review)),
        "_review_key": _review_key(review),
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
        select(UserManualReview)
        .options(
            joinedload(UserManualReview.user),
            joinedload(UserManualReview.literature_item).joinedload(ImportedLiteratureItem.memberships),
        )
        .where(
            or_(
                UserManualReview.review_interest_level != "",
                UserManualReview.review_interest_tag != "",
                UserManualReview.review_final_decision != "",
                UserManualReview.review_final_category != "",
                UserManualReview.reviewer_notes != "",
                UserManualReview.review_updated_at.is_not(None),
            )
        )
    )


def fetch_modified_reviews(db: Session) -> list[UserManualReview]:
    reviews = list(db.execute(_review_source_statement()).unique().scalars())
    return sorted(reviews, key=_review_sort_timestamp, reverse=True)


def build_user_review_records(db: Session) -> dict[int, list[dict[str, Any]]]:
    reviews = fetch_modified_reviews(db)
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for review in reviews:
        grouped[review.user_id].append(_build_review_record(review))
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
    reviews = fetch_modified_reviews(db)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for review in reviews:
        record = _build_review_record(review)
        grouped[str(record["_review_key"])].append(record)
    aggregated: list[dict[str, Any]] = []
    for key, records in grouped.items():
        ordered = sorted(records, key=lambda item: str(item.get("_review_updated_at") or ""), reverse=True)
        latest = dict(ordered[0])
        contributors = ", ".join(
            f'{record["_review_name"]}({record["_review_weight"]})'
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
                    f'[{record["_review_weight"]}] {record["_review_name"]} {record["_review_updated_at"]}: {detail}{suffix}'.strip()
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


def _user_review_stem(user: User) -> str:
    uid = _safe_segment(user.producer_uid or "")
    if uid != "user":
        return f"{uid}-data"
    return f"webuser-{user.id}-data"


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
        stem = _user_review_stem(user)
        user_dir_name = _safe_segment(user.producer_uid or f"webuser-{user.id}")
        current_paths = _export_record_set(records, current_root / "users" / user_dir_name, stem)
        archive_paths = _export_record_set(records, archive_root / "users" / user_dir_name, stem)
        per_user_outputs.append(
            {
                "user_id": user.id,
                "producer_uid": user.producer_uid,
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
    aggregate_current = _export_record_set(weighted_records, current_root / "aggregate", "aggregate-data")
    aggregate_archive = _export_record_set(weighted_records, archive_root / "aggregate", "aggregate-data")
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
