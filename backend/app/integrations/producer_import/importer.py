from __future__ import annotations

from dataclasses import dataclass
from datetime import date as date_type, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ...models import (
    ActionLog,
    ImportedDigestMembership,
    ImportedDigestRun,
    ImportedLiteratureItem,
    ProducerImportLedger,
)
from .artifact_validation import ArtifactValidationResult
from .mapper import map_item_payload, map_membership_payload
from .run_selection import SelectedProducerRun


@dataclass(frozen=True)
class ImportExecutionResult:
    digest_date: str
    source_run_id: str
    source_updated_at_utc: str
    result_status: str
    imported_items: int
    imported_memberships: int
    skipped_missing_key_count: int
    duplicate_membership_count: int
    conflict_count: int
    validation_status: str
    summary: dict[str, Any]


def _record_action(
    db: Session,
    *,
    action_type: str,
    entity_type: str,
    entity_id: int | None,
    detail: dict[str, Any],
) -> None:
    db.add(
        ActionLog(
            actor_user_id=None,
            target_user_id=None,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            detail_json=detail,
        )
    )


def _has_identity_conflict(existing: ImportedLiteratureItem, payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    conflicts: dict[str, dict[str, str]] = {}
    for field in ("doi", "canonical_url", "article_url"):
        current = str(getattr(existing, field) or "").strip()
        incoming = str(payload.get(field) or "").strip()
        if current and incoming and current != incoming:
            conflicts[field] = {"existing": current, "incoming": incoming}
    return conflicts


def _upsert_item(
    db: Session,
    *,
    payload: dict[str, Any],
    now: datetime,
) -> tuple[ImportedLiteratureItem, bool]:
    item = db.scalar(
        select(ImportedLiteratureItem).where(ImportedLiteratureItem.literature_item_key == payload["literature_item_key"])
    )
    created = False
    if item is None:
        item = ImportedLiteratureItem(
            literature_item_key=payload["literature_item_key"],
            first_seen_at=now,
        )
        db.add(item)
        db.flush()
        created = True
    item.doi = str(payload.get("doi") or "")
    item.canonical_url = str(payload.get("canonical_url") or "")
    item.article_url = str(payload.get("article_url") or "")
    item.journal = str(payload.get("journal") or "")
    item.publish_date = str(payload.get("publish_date") or "")
    item.publication_stage = str(payload.get("publication_stage") or "journal")
    item.category = str(payload.get("category") or "other")
    item.interest_level = str(payload.get("interest_level") or "一般")
    item.interest_score = int(payload.get("interest_score") or 3)
    item.interest_tag = str(payload.get("interest_tag") or "")
    item.title_en = str(payload.get("title_en") or "")
    item.title_zh = str(payload.get("title_zh") or "")
    item.summary_zh = str(payload.get("summary_zh") or "")
    item.abstract = str(payload.get("abstract") or "")
    item.source_id = str(payload.get("source_id") or "")
    item.publisher_family = str(payload.get("publisher_family") or "")
    item.group_name = str(payload.get("group_name") or "")
    item.authors_json = list(payload.get("authors_json") or [])
    item.tags_json = list(payload.get("tags_json") or [])
    item.extra_json = dict(payload.get("extra_json") or {})
    item.last_seen_at = now
    item.imported_at = now
    return item, created


def import_selected_run(
    db: Session,
    *,
    selected_run: SelectedProducerRun,
    validation: ArtifactValidationResult,
    trigger: str,
    force: bool = False,
) -> ImportExecutionResult:
    digest_date = date_type.fromisoformat(selected_run.run.digest_date)
    current_run = db.scalar(select(ImportedDigestRun).where(ImportedDigestRun.digest_date == digest_date))
    if (
        not force
        and current_run is not None
        and current_run.source_run_id == selected_run.run.run_id
        and current_run.source_updated_at_utc == selected_run.run.updated_at_utc
    ):
        return ImportExecutionResult(
            digest_date=selected_run.run.digest_date,
            source_run_id=selected_run.run.run_id,
            source_updated_at_utc=selected_run.run.updated_at_utc,
            result_status="noop",
            imported_items=0,
            imported_memberships=0,
            skipped_missing_key_count=0,
            duplicate_membership_count=0,
            conflict_count=0,
            validation_status=validation.status,
            summary={"reason": "already_current"},
        )

    now = datetime.utcnow()
    imported_items: set[str] = set()
    memberships: list[ImportedDigestMembership] = []
    membership_keys: set[tuple[str, str, str]] = set()
    skipped_missing_key_count = 0
    duplicate_membership_count = 0
    conflict_count = 0
    row_indexes: dict[str, int] = {}

    if current_run is None:
        current_run = ImportedDigestRun(digest_date=digest_date)
        db.add(current_run)
        db.flush()

    current_run.source_run_id = selected_run.run.run_id
    current_run.source_updated_at_utc = selected_run.run.updated_at_utc
    current_run.source_status = selected_run.run.status
    current_run.source_email_status = selected_run.run.email_status
    current_run.source_work_dir = selected_run.run.work_dir
    current_run.source_window_start_utc = selected_run.run.window_start_utc
    current_run.source_window_end_utc = selected_run.run.window_end_utc
    current_run.metadata_json = dict(selected_run.run.metadata_json)
    current_run.artifact_validation_status = validation.status
    current_run.artifact_validation_json = dict(validation.payload)
    current_run.imported_at = now

    db.execute(delete(ImportedDigestMembership).where(ImportedDigestMembership.digest_date == digest_date))

    for record in selected_run.records:
        key = record.unique_key.strip()
        if not key:
            skipped_missing_key_count += 1
            _record_action(
                db,
                action_type="producer_import_skip_missing_key",
                entity_type="producer_record",
                entity_id=record.record_id,
                detail={
                    "digest_date": selected_run.run.digest_date,
                    "run_id": selected_run.run.run_id,
                    "list_type": record.list_type,
                    "record_id": record.record_id,
                },
            )
            continue

        item_payload = map_item_payload(record)
        existing_item = db.scalar(
            select(ImportedLiteratureItem).where(ImportedLiteratureItem.literature_item_key == item_payload["literature_item_key"])
        )
        if existing_item is not None:
            conflicts = _has_identity_conflict(existing_item, item_payload)
            if conflicts:
                conflict_count += 1
                _record_action(
                    db,
                    action_type="producer_import_key_conflict",
                    entity_type="literature_item",
                    entity_id=existing_item.id,
                    detail={
                        "digest_date": selected_run.run.digest_date,
                        "run_id": selected_run.run.run_id,
                        "literature_item_key": key,
                        "conflicts": conflicts,
                    },
                )
        item, _ = _upsert_item(db, payload=item_payload, now=now)
        imported_items.add(item.literature_item_key)

        membership_key = (selected_run.run.digest_date, record.list_type, key)
        if membership_key in membership_keys:
            duplicate_membership_count += 1
            _record_action(
                db,
                action_type="producer_import_duplicate_membership",
                entity_type="producer_record",
                entity_id=record.record_id,
                detail={
                    "digest_date": selected_run.run.digest_date,
                    "run_id": selected_run.run.run_id,
                    "membership_key": membership_key,
                },
            )
            continue
        membership_keys.add(membership_key)
        row_indexes[record.list_type] = row_indexes.get(record.list_type, 0) + 1
        membership_payload = map_membership_payload(record, row_index=row_indexes[record.list_type])
        memberships.append(
            ImportedDigestMembership(
                digest_run_id=current_run.id,
                literature_item_id=item.id,
                literature_item_key=item.literature_item_key,
                digest_date=digest_date,
                list_type=str(membership_payload["list_type"]),
                publication_stage=str(membership_payload["publication_stage"]),
                decision=str(membership_payload["decision"]),
                row_index=int(membership_payload["row_index"]),
                source_record_json=dict(membership_payload["source_record_json"] or {}),
            )
        )

    db.add_all(memberships)
    summary = {
        "trigger": trigger,
        "force": force,
        "digest_date": selected_run.run.digest_date,
        "source_run_id": selected_run.run.run_id,
        "source_updated_at_utc": selected_run.run.updated_at_utc,
        "imported_item_keys": len(imported_items),
        "imported_memberships": len(memberships),
        "skipped_missing_keys": skipped_missing_key_count,
        "duplicate_memberships": duplicate_membership_count,
        "conflicts": conflict_count,
        "validation": validation.payload,
    }
    ledger = ProducerImportLedger(
        digest_date=digest_date,
        source_run_id=selected_run.run.run_id,
        source_updated_at_utc=selected_run.run.updated_at_utc,
        trigger=trigger,
        result_status="completed",
        validation_status=validation.status,
        imported_items_count=len(imported_items),
        imported_memberships_count=len(memberships),
        skipped_missing_key_count=skipped_missing_key_count,
        duplicate_membership_count=duplicate_membership_count,
        conflict_count=conflict_count,
        summary_json=summary,
    )
    db.add(ledger)
    _record_action(
        db,
        action_type="producer_import_completed",
        entity_type="digest_run",
        entity_id=current_run.id,
        detail=summary,
    )
    db.commit()
    return ImportExecutionResult(
        digest_date=selected_run.run.digest_date,
        source_run_id=selected_run.run.run_id,
        source_updated_at_utc=selected_run.run.updated_at_utc,
        result_status="completed",
        imported_items=len(imported_items),
        imported_memberships=len(memberships),
        skipped_missing_key_count=skipped_missing_key_count,
        duplicate_membership_count=duplicate_membership_count,
        conflict_count=conflict_count,
        validation_status=validation.status,
        summary=summary,
    )
