from __future__ import annotations

from contextlib import contextmanager, suppress
from dataclasses import dataclass
from datetime import datetime
import fcntl
from pathlib import Path
from typing import Callable, Iterator
from zoneinfo import ZoneInfo

from ... import database
from ...config import PROJECT_ROOT, Settings, get_settings, parse_clock_hhmm
from ...migrations import run_runtime_migrations
from instance_paths import get_instance_paths
from .importer import ImportExecutionResult
from .service import check_and_import_latest_runs, sync_users_from_producer_sources


Logger = Callable[[str], None]


@dataclass(frozen=True)
class RuntimeSyncResult:
    trigger: str
    imported_run_count: int
    imported_memberships: int
    imported_dates: list[str]
    skipped_locked: bool = False


def runtime_sync_lock_file() -> Path:
    paths = get_instance_paths(PROJECT_ROOT)
    lock_path = paths.web_runtime_dir / "producer-sync.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    return lock_path


@contextmanager
def acquire_runtime_sync_lock(*, blocking: bool = False) -> Iterator[bool]:
    lock_path = runtime_sync_lock_file()
    handle = lock_path.open("a+b")
    flags = fcntl.LOCK_EX
    if not blocking:
        flags |= fcntl.LOCK_NB
    acquired = False
    try:
        try:
            fcntl.flock(handle.fileno(), flags)
            acquired = True
        except BlockingIOError:
            yield False
            return
        yield True
    finally:
        if acquired:
            with suppress(OSError):
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def ensure_runtime_database_ready() -> None:
    database.configure_database()
    run_runtime_migrations(database.engine)
    database.Base.metadata.create_all(bind=database.engine)


def inside_sync_window(settings: Settings, *, now: datetime | None = None) -> bool:
    local_now = (now or datetime.now(ZoneInfo(settings.cst_timezone))).astimezone(ZoneInfo(settings.cst_timezone))
    start_hour, start_minute = parse_clock_hhmm(settings.producer_sync_window_start)
    end_hour, end_minute = parse_clock_hhmm(settings.producer_sync_window_end)
    window_start = local_now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
    window_end = local_now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
    if window_end <= window_start:
        return local_now >= window_start or local_now < window_end
    return window_start <= local_now < window_end


def sync_from_producer(
    *,
    trigger: str = "startup",
    logger: Logger = print,
    blocking: bool = False,
) -> RuntimeSyncResult:
    settings = get_settings()
    if not settings.producer_sync_enabled:
        return RuntimeSyncResult(
            trigger=trigger,
            imported_run_count=0,
            imported_memberships=0,
            imported_dates=[],
        )

    if database.SessionLocal is None or database.engine is None:
        ensure_runtime_database_ready()

    with acquire_runtime_sync_lock(blocking=blocking) as acquired:
        if not acquired:
            logger(f"[producer-sync] trigger={trigger} skipped=locked")
            return RuntimeSyncResult(
                trigger=trigger,
                imported_run_count=0,
                imported_memberships=0,
                imported_dates=[],
                skipped_locked=True,
            )

        if database.SessionLocal is None:
            return RuntimeSyncResult(
                trigger=trigger,
                imported_run_count=0,
                imported_memberships=0,
                imported_dates=[],
            )

        with database.SessionLocal() as db:
            sync_users_from_producer_sources(db)
            results = check_and_import_latest_runs(db, trigger=trigger)

        imported_dates = [result.digest_date for result in results]
        imported_memberships = sum(result.imported_memberships for result in results)
        if results:
            logger(
                f"[producer-sync] trigger={trigger} imported_runs={len(results)} "
                f"imported_memberships={imported_memberships} dates={', '.join(imported_dates)}"
            )
        return RuntimeSyncResult(
            trigger=trigger,
            imported_run_count=len(results),
            imported_memberships=imported_memberships,
            imported_dates=imported_dates,
        )
