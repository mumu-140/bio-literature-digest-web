from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from instance_paths import InstancePaths

from .source_reader import ProducerRun


@dataclass(frozen=True)
class ArtifactValidationResult:
    status: str
    payload: dict[str, object]


def _archive_candidates(paths: InstancePaths, run: ProducerRun) -> list[Path]:
    candidates = [paths.producer_archive_dir / run.digest_date]
    work_dir = Path(run.work_dir) if run.work_dir else None
    if work_dir is not None:
        candidates.append(work_dir)
    return candidates


def validate_run_artifacts(paths: InstancePaths, run: ProducerRun) -> ArtifactValidationResult:
    candidates = _archive_candidates(paths, run)
    existing = [path for path in candidates if path.exists()]
    file_count = 0
    for path in existing:
        if path.is_dir():
            file_count += sum(1 for item in path.iterdir())
        else:
            file_count += 1
    if existing and file_count > 0:
        status = "ok"
    elif existing:
        status = "partial"
    else:
        status = "pending"
    return ArtifactValidationResult(
        status=status,
        payload={
            "checked_paths": [str(path) for path in candidates],
            "existing_paths": [str(path) for path in existing],
            "existing_file_count": file_count,
        },
    )
