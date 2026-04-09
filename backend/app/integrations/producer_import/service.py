from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...config import PROJECT_ROOT
from ...models import ImportedDigestRun
from instance_paths import get_instance_paths
from .artifact_validation import validate_run_artifacts
from .importer import ImportExecutionResult, import_selected_run
from .run_selection import latest_usable_runs_by_date, selected_run_by_id
from .source_reader import load_snapshot
from .user_sync import sync_users_from_producer_config


class ImportStatusError(RuntimeError):
    pass


@dataclass(frozen=True)
class RunStatus:
    digest_date: str
    run_id: str
    updated_at_utc: str
    status: str
    email_status: str
    work_dir: str
    validation_status: str
    validation_payload: dict[str, object]
    record_count: int
    is_current: bool
    current_local_run_id: str
    current_local_updated_at_utc: str


def sync_users_from_producer_sources(db: Session) -> None:
    paths = get_instance_paths(PROJECT_ROOT)
    config_path = paths.producer_users_config if paths.producer_users_config.exists() else paths.producer_email_config
    if config_path.exists():
        sync_users_from_producer_config(db, config_path=config_path)


def check_and_import_latest_runs(db: Session, *, trigger: str) -> list[ImportExecutionResult]:
    paths = get_instance_paths(PROJECT_ROOT)
    snapshot = load_snapshot(paths.producer_database_file)
    results: list[ImportExecutionResult] = []
    for selected in latest_usable_runs_by_date(snapshot.runs, snapshot.records_by_run):
        validation = validate_run_artifacts(paths, selected.run)
        result = import_selected_run(db, selected_run=selected, validation=validation, trigger=trigger)
        if result.result_status != "noop":
            results.append(result)
    return results


def import_run_by_id(db: Session, *, run_id: str, trigger: str, force: bool = False) -> ImportExecutionResult:
    paths = get_instance_paths(PROJECT_ROOT)
    snapshot = load_snapshot(paths.producer_database_file)
    selected = selected_run_by_id(snapshot.runs, snapshot.records_by_run, run_id)
    if selected is None:
        raise ImportStatusError(f"Run {run_id} is not importable")
    validation = validate_run_artifacts(paths, selected.run)
    return import_selected_run(db, selected_run=selected, validation=validation, trigger=trigger, force=force)


def list_run_statuses(db: Session) -> list[RunStatus]:
    paths = get_instance_paths(PROJECT_ROOT)
    snapshot = load_snapshot(paths.producer_database_file)
    local_by_date = {
        str(run.digest_date): run
        for run in db.scalars(select(ImportedDigestRun).order_by(ImportedDigestRun.digest_date.desc())).all()
    }
    rows: list[RunStatus] = []
    for selected in latest_usable_runs_by_date(snapshot.runs, snapshot.records_by_run):
        validation = validate_run_artifacts(paths, selected.run)
        current = local_by_date.get(selected.run.digest_date)
        rows.append(
            RunStatus(
                digest_date=selected.run.digest_date,
                run_id=selected.run.run_id,
                updated_at_utc=selected.run.updated_at_utc,
                status=selected.run.status,
                email_status=selected.run.email_status,
                work_dir=selected.run.work_dir,
                validation_status=validation.status,
                validation_payload=dict(validation.payload),
                record_count=len(selected.records),
                is_current=bool(
                    current
                    and current.source_run_id == selected.run.run_id
                    and current.source_updated_at_utc == selected.run.updated_at_utc
                ),
                current_local_run_id=current.source_run_id if current else "",
                current_local_updated_at_utc=current.source_updated_at_utc if current else "",
            )
        )
    return rows
