from __future__ import annotations

import csv
import json
import os
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import select

from app.config import reset_settings_cache
from app import database
from app.models import DigestRun, Favorite, Paper, PaperDailyEntry, User
from app.services.importer import import_digest_run


class ImporterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="bio-digest-web-import-")
        self.root = Path(self.tmpdir.name)
        reset_settings_cache()
        database.configure_database(f"sqlite:///{self.root / 'test.db'}")
        database.Base.metadata.create_all(bind=database.engine)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()
        os.environ.pop("DATA_RETENTION_DAYS", None)

    def write_run(self, run_date: str, doi: str) -> Path:
        run_dir = self.root / run_date
        run_dir.mkdir()
        metadata = {
            "status": "success",
            "email_status": "sent",
            "finished_at_utc": f"{run_date}T00:30:00Z",
            "window": {"start_utc": f"{run_date}T00:00:00Z", "end_utc": f"{run_date}T00:30:00Z"},
        }
        (run_dir / "run_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        with (run_dir / "digest.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
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
                    "tags",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "journal": "Nature",
                    "publish_date": f"{run_date}T00:01:00Z",
                    "category": "omics",
                    "interest_level": "感兴趣",
                    "interest_tag": "单细胞",
                    "title_en": f"A paper {run_date}",
                    "title_zh": f"论文 {run_date}",
                    "summary_zh": "摘要",
                    "abstract": "Abstract",
                    "doi": doi,
                    "article_url": f"https://example.org/{doi}",
                    "tags": "single-cell, plant",
                }
            )
        return run_dir

    def test_import_digest_run(self) -> None:
        run_dir = self.write_run("2026-04-06", "10.1000/test")
        with database.SessionLocal() as db:
            digest_run, imported = import_digest_run(db, run_dir)
        self.assertEqual(imported, 1)
        self.assertEqual(str(digest_run.digest_date), "2026-04-06")

    def test_import_retains_recent_window_only(self) -> None:
        os.environ["DATA_RETENTION_DAYS"] = "2"
        reset_settings_cache()
        run_dirs = [
            self.write_run("2026-04-04", "10.1000/a"),
            self.write_run("2026-04-05", "10.1000/b"),
            self.write_run("2026-04-06", "10.1000/c"),
        ]
        with database.SessionLocal() as db:
            for run_dir in run_dirs:
                import_digest_run(db, run_dir)
            kept_dates = [str(item.digest_date) for item in db.query(DigestRun).order_by(DigestRun.digest_date.asc()).all()]
            kept_entries = [str(item.digest_date) for item in db.query(PaperDailyEntry).order_by(PaperDailyEntry.digest_date.asc()).all()]
        self.assertEqual(kept_dates, ["2026-04-05", "2026-04-06"])
        self.assertEqual(kept_entries, ["2026-04-05", "2026-04-06"])

    def test_import_preserves_favorited_history_beyond_window(self) -> None:
        os.environ["DATA_RETENTION_DAYS"] = "2"
        reset_settings_cache()
        run_dirs = [
            self.write_run("2026-04-04", "10.1000/favorite"),
            self.write_run("2026-04-05", "10.1000/b"),
            self.write_run("2026-04-06", "10.1000/c"),
        ]
        with database.SessionLocal() as db:
            import_digest_run(db, run_dirs[0])
            paper = db.scalar(select(Paper))
            user = User(email="member@example.com", name="Member", password_hash="hashed")
            db.add(user)
            db.flush()
            db.add(Favorite(user_id=user.id, paper_id=paper.id))
            db.commit()
            import_digest_run(db, run_dirs[1])
            import_digest_run(db, run_dirs[2])
            kept_dates = [str(item.digest_date) for item in db.query(DigestRun).order_by(DigestRun.digest_date.asc()).all()]
            kept_entries = [str(item.digest_date) for item in db.query(PaperDailyEntry).order_by(PaperDailyEntry.digest_date.asc()).all()]
        self.assertEqual(kept_dates, ["2026-04-04", "2026-04-05", "2026-04-06"])
        self.assertEqual(kept_entries, ["2026-04-04", "2026-04-05", "2026-04-06"])


if __name__ == "__main__":
    unittest.main()
