#!/usr/bin/env python3
from __future__ import annotations

import argparse
import signal
import time

from app.config import get_settings
from app.integrations.producer_import.runtime_sync import (
    ensure_runtime_database_ready,
    inside_sync_window,
    sync_from_producer,
)


_STOP_REQUESTED = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the producer import sync loop for the web workspace."
    )
    parser.add_argument("--interval-seconds", type=int, default=None)
    parser.add_argument("--run-once", action="store_true")
    parser.add_argument("--skip-initial-sync", action="store_true")
    parser.add_argument("--recent-runs", type=int, default=0, help="Legacy compatibility flag; ignored.")
    parser.add_argument("--require-email-sent", action="store_true", help="Legacy compatibility flag; ignored.")
    return parser.parse_args()


def _handle_stop(_signum, _frame) -> None:
    global _STOP_REQUESTED
    _STOP_REQUESTED = True


def main() -> int:
    args = parse_args()
    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    ensure_runtime_database_ready()
    settings = get_settings()
    interval_seconds = (
        args.interval_seconds
        if args.interval_seconds is not None
        else max(1, int(settings.producer_sync_interval_seconds or 60))
    )

    print(
        "[producer-sync-daemon] starting "
        f"interval={interval_seconds}s "
        f"window={settings.producer_sync_window_start}-{settings.producer_sync_window_end} "
        f"timezone={settings.cst_timezone}"
    )

    if not args.skip_initial_sync:
        sync_from_producer(trigger="daemon-startup")

    if args.run_once:
        return 0

    while not _STOP_REQUESTED:
        time.sleep(interval_seconds)
        if _STOP_REQUESTED:
            break
        settings = get_settings()
        if not settings.producer_sync_enabled:
            continue
        if not inside_sync_window(settings):
            continue
        sync_from_producer(trigger="daemon-periodic")

    print("[producer-sync-daemon] stopping")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
