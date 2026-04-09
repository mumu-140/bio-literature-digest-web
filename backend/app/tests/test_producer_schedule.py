from __future__ import annotations

import unittest

from app.integrations.producer_import.run_selection import latest_usable_runs_by_date
from app.integrations.producer_import.source_reader import ProducerPaperRecord, ProducerRun


def _run(run_id: str, digest_date: str, updated_at_utc: str) -> ProducerRun:
    return ProducerRun(
        run_id=run_id,
        digest_date=digest_date,
        status="success",
        email_status="sent",
        window_start_utc="",
        window_end_utc="",
        work_dir="",
        metadata_json={},
        updated_at_utc=updated_at_utc,
    )


def _record(run_id: str, digest_date: str, record_id: int) -> ProducerPaperRecord:
    return ProducerPaperRecord(
        record_id=record_id,
        run_id=run_id,
        digest_date=digest_date,
        list_type="digest",
        unique_key=f"doi:10.1000/{record_id}",
        journal="Nature",
        publish_date="2026-04-09",
        category="omics",
        interest_level="感兴趣",
        interest_tag="tag",
        title_en="Title",
        title_zh="标题",
        summary_zh="摘要",
        abstract="abstract",
        doi=f"10.1000/{record_id}",
        article_url="https://example.org/paper",
        tags="tag-a,tag-b",
        updated_at_utc="2026-04-09T00:00:00Z",
        article_url_norm="https://example.org/paper",
        paper_article_url="https://example.org/paper",
        paper_doi=f"10.1000/{record_id}",
        paper_journal="Nature",
        row_json={"publication_stage": "journal"},
    )


class ProducerScheduleTest(unittest.TestCase):
    def test_latest_usable_run_wins_by_updated_at(self) -> None:
        runs = [
            _run("old", "2026-04-09", "2026-04-09T00:00:00Z"),
            _run("new", "2026-04-09", "2026-04-09T01:00:00Z"),
        ]
        records_by_run = {
            "old": [_record("old", "2026-04-09", 1)],
            "new": [_record("new", "2026-04-09", 2)],
        }
        selected = latest_usable_runs_by_date(runs, records_by_run)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].run.run_id, "new")

    def test_runs_without_records_are_ignored(self) -> None:
        runs = [
            _run("empty", "2026-04-09", "2026-04-09T02:00:00Z"),
            _run("usable", "2026-04-09", "2026-04-09T01:00:00Z"),
        ]
        records_by_run = {
            "empty": [],
            "usable": [_record("usable", "2026-04-09", 3)],
        }
        selected = latest_usable_runs_by_date(runs, records_by_run)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].run.run_id, "usable")


if __name__ == "__main__":
    unittest.main()
