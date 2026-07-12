from __future__ import annotations

from dataclasses import dataclass

from .source_reader import ProducerPaperRecord, ProducerRun


@dataclass(frozen=True)
class SelectedProducerRun:
    run: ProducerRun
    records: list[ProducerPaperRecord]


def _sort_key(run: ProducerRun) -> tuple[str, str, str]:
    return (run.digest_date, run.updated_at_utc, run.run_id)


def is_usable_run(run: ProducerRun, records: list[ProducerPaperRecord] | None) -> bool:
    return bool(run.run_id and run.digest_date and records)


def latest_usable_runs_by_date(
    runs: list[ProducerRun],
    records_by_run: dict[str, list[ProducerPaperRecord]],
) -> list[SelectedProducerRun]:
    latest: dict[str, SelectedProducerRun] = {}
    for run in sorted(runs, key=_sort_key):
        records = records_by_run.get(run.run_id, [])
        if not is_usable_run(run, records):
            continue
        latest[run.digest_date] = SelectedProducerRun(run=run, records=records)
    return sorted(latest.values(), key=lambda item: (item.run.digest_date, item.run.updated_at_utc), reverse=True)


def selected_run_by_id(
    runs: list[ProducerRun],
    records_by_run: dict[str, list[ProducerPaperRecord]],
    run_id: str,
) -> SelectedProducerRun | None:
    for run in runs:
        if run.run_id != run_id:
            continue
        records = records_by_run.get(run.run_id, [])
        if not is_usable_run(run, records):
            return None
        return SelectedProducerRun(run=run, records=records)
    return None
