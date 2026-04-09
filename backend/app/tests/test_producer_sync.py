from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app import database
from app.integrations.producer_import.service import check_and_import_latest_runs, import_run_by_id
from app.models import (
    ImportedDigestMembership,
    ImportedDigestRun,
    ImportedLiteratureItem,
    ProducerImportLedger,
    User,
    UserLiteratureFavorite,
    UserManualReview,
)


class ProducerSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="bio-digest-web-producer-sync-")
        self.root = Path(self.tmpdir.name)
        self.local_db_path = self.root / "local.db"
        self.producer_db_path = self.root / "producer.db"
        self.archive_dir = self.root / "archives"
        self.archive_dir.mkdir()
        os.environ["BIO_DIGEST_PRODUCER_DATABASE_FILE"] = str(self.producer_db_path)
        os.environ["BIO_DIGEST_PRODUCER_ARCHIVE_DIR"] = str(self.archive_dir)
        database.configure_database(f"sqlite:///{self.local_db_path}")
        database.Base.metadata.create_all(bind=database.engine)
        self._create_producer_database()

    def tearDown(self) -> None:
        self.tmpdir.cleanup()
        os.environ.pop("BIO_DIGEST_PRODUCER_DATABASE_FILE", None)
        os.environ.pop("BIO_DIGEST_PRODUCER_ARCHIVE_DIR", None)
        database.engine = None
        database.SessionLocal = None

    def _create_producer_database(self) -> None:
        with sqlite3.connect(str(self.producer_db_path)) as connection:
            connection.executescript(
                """
                CREATE TABLE runs (
                  run_id TEXT PRIMARY KEY,
                  archive_date TEXT NOT NULL,
                  status TEXT,
                  email_status TEXT,
                  window_start_utc TEXT,
                  window_end_utc TEXT,
                  work_dir TEXT,
                  metadata_json TEXT,
                  updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE papers (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  unique_key TEXT UNIQUE,
                  doi_norm TEXT,
                  article_url_norm TEXT,
                  title_norm TEXT,
                  journal_norm TEXT,
                  title_en TEXT,
                  article_url TEXT,
                  doi TEXT,
                  journal TEXT,
                  created_at_utc TEXT NOT NULL,
                  updated_at_utc TEXT NOT NULL
                );

                CREATE TABLE paper_records (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  run_id TEXT NOT NULL,
                  archive_date TEXT NOT NULL,
                  dataset TEXT NOT NULL,
                  paper_id INTEGER NOT NULL,
                  journal TEXT,
                  publish_date TEXT,
                  category TEXT,
                  interest_level TEXT,
                  interest_tag TEXT,
                  title_en TEXT,
                  title_zh TEXT,
                  summary_zh TEXT,
                  abstract TEXT,
                  doi TEXT,
                  article_url TEXT,
                  tags TEXT,
                  llm_decision TEXT,
                  review_final_decision TEXT,
                  review_final_category TEXT,
                  reviewer_notes TEXT,
                  row_json TEXT NOT NULL,
                  updated_at_utc TEXT NOT NULL
                );
                """
            )
            connection.execute(
                """
                INSERT INTO runs (
                  run_id, archive_date, status, email_status, window_start_utc, window_end_utc, work_dir, metadata_json, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "2026-04-09:old",
                    "2026-04-09",
                    "success",
                    "sent",
                    "",
                    "",
                    str(self.root / "run-old"),
                    json.dumps({"source": "old"}, ensure_ascii=False),
                    "2026-04-09T00:00:00Z",
                ),
            )
            connection.execute(
                """
                INSERT INTO runs (
                  run_id, archive_date, status, email_status, window_start_utc, window_end_utc, work_dir, metadata_json, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "2026-04-09:new",
                    "2026-04-09",
                    "success",
                    "sent",
                    "",
                    "",
                    str(self.root / "run-new"),
                    json.dumps({"source": "new"}, ensure_ascii=False),
                    "2026-04-09T01:00:00Z",
                ),
            )
            connection.execute(
                """
                INSERT INTO papers (
                  unique_key, doi_norm, article_url_norm, title_norm, journal_norm, title_en, article_url, doi, journal, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "doi:10.1000/test",
                    "10.1000/test",
                    "https://example.org/paper",
                    "new title",
                    "nature",
                    "New title",
                    "https://example.org/paper",
                    "10.1000/test",
                    "Nature",
                    "2026-04-09T00:00:00Z",
                    "2026-04-09T00:00:00Z",
                ),
            )
            connection.execute(
                """
                INSERT INTO papers (
                  unique_key, doi_norm, article_url_norm, title_norm, journal_norm, title_en, article_url, doi, journal, created_at_utc, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    None,
                    None,
                    "https://example.org/missing",
                    "missing key",
                    "nature",
                    "Missing key title",
                    "https://example.org/missing",
                    "",
                    "Nature",
                    "2026-04-09T00:00:00Z",
                    "2026-04-09T00:00:00Z",
                ),
            )
            first_paper_id = int(connection.execute("SELECT id FROM papers WHERE unique_key = 'doi:10.1000/test'").fetchone()[0])
            missing_key_paper_id = int(connection.execute("SELECT id FROM papers WHERE unique_key IS NULL").fetchone()[0])
            connection.execute(
                """
                INSERT INTO paper_records (
                  run_id, archive_date, dataset, paper_id, journal, publish_date, category, interest_level, interest_tag,
                  title_en, title_zh, summary_zh, abstract, doi, article_url, tags, llm_decision,
                  review_final_decision, review_final_category, reviewer_notes, row_json, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "2026-04-09:old",
                    "2026-04-09",
                    "digest",
                    first_paper_id,
                    "Nature",
                    "2026-04-08T00:00:00Z",
                    "omics",
                    "一般",
                    "旧标签",
                    "Old title",
                    "旧标题",
                    "旧摘要",
                    "Old abstract",
                    "10.1000/test",
                    "https://example.org/paper",
                    "legacy",
                    "",
                    "",
                    "",
                    "",
                    json.dumps({"publication_stage": "journal", "authors": ["Old Author"]}, ensure_ascii=False),
                    "2026-04-09T00:00:00Z",
                ),
            )
            connection.execute(
                """
                INSERT INTO paper_records (
                  run_id, archive_date, dataset, paper_id, journal, publish_date, category, interest_level, interest_tag,
                  title_en, title_zh, summary_zh, abstract, doi, article_url, tags, llm_decision,
                  review_final_decision, review_final_category, reviewer_notes, row_json, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "2026-04-09:new",
                    "2026-04-09",
                    "digest",
                    first_paper_id,
                    "Nature",
                    "2026-04-08T00:00:00Z",
                    "microbe-immunity",
                    "感兴趣",
                    "生物通络",
                    "New title",
                    "新标题",
                    "新摘要",
                    "New abstract",
                    "10.1000/test",
                    "https://example.org/paper",
                    "tag-a,tag-b",
                    "",
                    "",
                    "",
                    "",
                    json.dumps({"publication_stage": "preprint", "authors": ["Author A", "Author B"]}, ensure_ascii=False),
                    "2026-04-09T01:00:00Z",
                ),
            )
            connection.execute(
                """
                INSERT INTO paper_records (
                  run_id, archive_date, dataset, paper_id, journal, publish_date, category, interest_level, interest_tag,
                  title_en, title_zh, summary_zh, abstract, doi, article_url, tags, llm_decision,
                  review_final_decision, review_final_category, reviewer_notes, row_json, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "2026-04-09:new",
                    "2026-04-09",
                    "digest",
                    missing_key_paper_id,
                    "Nature",
                    "2026-04-08T00:00:00Z",
                    "microbe-immunity",
                    "一般",
                    "跳过",
                    "Missing title",
                    "缺失键标题",
                    "缺失键摘要",
                    "Missing abstract",
                    "",
                    "https://example.org/missing",
                    "tag-c",
                    "",
                    "",
                    "",
                    "",
                    json.dumps({"publication_stage": "preprint"}, ensure_ascii=False),
                    "2026-04-09T01:00:00Z",
                ),
            )
            connection.execute(
                """
                INSERT INTO paper_records (
                  run_id, archive_date, dataset, paper_id, journal, publish_date, category, interest_level, interest_tag,
                  title_en, title_zh, summary_zh, abstract, doi, article_url, tags, llm_decision,
                  review_final_decision, review_final_category, reviewer_notes, row_json, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "2026-04-09:new",
                    "2026-04-09",
                    "daily_review",
                    first_paper_id,
                    "Nature",
                    "2026-04-08T00:00:00Z",
                    "microbe-immunity",
                    "非常感兴趣",
                    "重点复核",
                    "New title",
                    "新标题",
                    "新摘要",
                    "New abstract",
                    "10.1000/test",
                    "https://example.org/paper",
                    "tag-a,tag-b",
                    "",
                    "keep",
                    "microbe-immunity",
                    "looks good",
                    json.dumps({"publication_stage": "preprint", "authors": ["Author A", "Author B"]}, ensure_ascii=False),
                    "2026-04-09T01:00:00Z",
                ),
            )
            connection.commit()

    def test_check_and_import_latest_runs_imports_latest_local_run(self) -> None:
        with database.SessionLocal() as db:
            results = check_and_import_latest_runs(db, trigger="startup")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].source_run_id, "2026-04-09:new")
        self.assertEqual(results[0].skipped_missing_key_count, 1)

        with database.SessionLocal() as db:
            digest_run = db.scalar(select(ImportedDigestRun).where(ImportedDigestRun.digest_date == date(2026, 4, 9)))
            item = db.scalar(
                select(ImportedLiteratureItem).where(ImportedLiteratureItem.literature_item_key == "doi:10.1000/test")
            )
            memberships = list(
                db.scalars(
                    select(ImportedDigestMembership)
                    .where(ImportedDigestMembership.digest_date == date(2026, 4, 9))
                    .order_by(ImportedDigestMembership.list_type.asc(), ImportedDigestMembership.row_index.asc())
                )
            )
            ledger_rows = list(db.scalars(select(ProducerImportLedger).order_by(ProducerImportLedger.id.asc())))

        self.assertIsNotNone(digest_run)
        self.assertEqual(digest_run.metadata_json.get("source"), "new")
        self.assertEqual(digest_run.artifact_validation_status, "pending")
        self.assertIsNotNone(item)
        self.assertEqual(item.title_en, "New title")
        self.assertEqual(item.interest_score, 4)
        self.assertEqual(item.publication_stage, "preprint")
        self.assertEqual(item.tags_json, ["tag-a", "tag-b"])
        self.assertEqual(item.authors_json, ["Author A", "Author B"])
        self.assertEqual([(membership.list_type, membership.row_index) for membership in memberships], [("daily_review", 1), ("digest", 1)])
        self.assertEqual(len(ledger_rows), 1)

    def test_reimport_same_run_replaces_memberships_and_appends_ledger(self) -> None:
        with database.SessionLocal() as db:
            first = check_and_import_latest_runs(db, trigger="startup")
            second = import_run_by_id(db, run_id="2026-04-09:new", trigger="reimport", force=True)
            ledger_rows = list(db.scalars(select(ProducerImportLedger).order_by(ProducerImportLedger.id.asc())))
        self.assertEqual(len(first), 1)
        self.assertEqual(second.result_status, "completed")
        self.assertEqual(len(ledger_rows), 2)

    def test_reimport_preserves_favorite_and_manual_review_by_canonical_key(self) -> None:
        with database.SessionLocal() as db:
            check_and_import_latest_runs(db, trigger="startup")
            user = User(
                email="member@example.com",
                name="Member",
                password_hash="passwordless",
                role="member",
                is_active=True,
            )
            db.add(user)
            db.flush()
            item = db.scalar(select(ImportedLiteratureItem).where(ImportedLiteratureItem.literature_item_key == "doi:10.1000/test"))
            self.assertIsNotNone(item)
            db.add(
                UserLiteratureFavorite(
                    user_id=user.id,
                    literature_item_id=item.id,
                    literature_item_key=item.literature_item_key,
                )
            )
            db.add(
                UserManualReview(
                    user_id=user.id,
                    literature_item_id=item.id,
                    literature_item_key=item.literature_item_key,
                    review_interest_level="非常感兴趣",
                    review_final_decision="keep",
                    review_final_category="microbe-immunity",
                    reviewer_notes="keep this one",
                )
            )
            db.commit()

        with sqlite3.connect(str(self.producer_db_path)) as connection:
            connection.execute(
                """
                INSERT INTO runs (
                  run_id, archive_date, status, email_status, window_start_utc, window_end_utc, work_dir, metadata_json, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "2026-04-09:replacement",
                    "2026-04-09",
                    "success",
                    "sent",
                    "",
                    "",
                    str(self.root / "run-replacement"),
                    json.dumps({"source": "replacement"}, ensure_ascii=False),
                    "2026-04-09T02:00:00Z",
                ),
            )
            paper_id = int(connection.execute("SELECT id FROM papers WHERE unique_key = 'doi:10.1000/test'").fetchone()[0])
            connection.execute(
                """
                INSERT INTO paper_records (
                  run_id, archive_date, dataset, paper_id, journal, publish_date, category, interest_level, interest_tag,
                  title_en, title_zh, summary_zh, abstract, doi, article_url, tags, llm_decision,
                  review_final_decision, review_final_category, reviewer_notes, row_json, updated_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "2026-04-09:replacement",
                    "2026-04-09",
                    "digest",
                    paper_id,
                    "Nature",
                    "2026-04-08T00:00:00Z",
                    "plant-biology",
                    "非常感兴趣",
                    "更新标签",
                    "Updated title",
                    "更新标题",
                    "更新摘要",
                    "Updated abstract",
                    "10.1000/test",
                    "https://example.org/paper",
                    "tag-z",
                    "",
                    "",
                    "",
                    "",
                    json.dumps({"publication_stage": "journal", "authors": ["Author Z"]}, ensure_ascii=False),
                    "2026-04-09T02:00:00Z",
                ),
            )
            connection.commit()

        with database.SessionLocal() as db:
            result = import_run_by_id(db, run_id="2026-04-09:replacement", trigger="reimport", force=True)
            digest_run = db.scalar(select(ImportedDigestRun).where(ImportedDigestRun.digest_date == date(2026, 4, 9)))
            item = db.scalar(select(ImportedLiteratureItem).where(ImportedLiteratureItem.literature_item_key == "doi:10.1000/test"))
            memberships = list(
                db.scalars(
                    select(ImportedDigestMembership)
                    .where(ImportedDigestMembership.digest_date == date(2026, 4, 9))
                    .order_by(ImportedDigestMembership.list_type.asc(), ImportedDigestMembership.row_index.asc())
                )
            )
            favorite = db.scalar(
                select(UserLiteratureFavorite).where(UserLiteratureFavorite.literature_item_key == "doi:10.1000/test")
            )
            review = db.scalar(select(UserManualReview).where(UserManualReview.literature_item_key == "doi:10.1000/test"))

        self.assertEqual(result.result_status, "completed")
        self.assertIsNotNone(digest_run)
        self.assertEqual(digest_run.source_run_id, "2026-04-09:replacement")
        self.assertIsNotNone(item)
        self.assertEqual(item.title_en, "Updated title")
        self.assertEqual(item.category, "plant-biology")
        self.assertEqual(item.authors_json, ["Author Z"])
        self.assertEqual([(membership.list_type, membership.literature_item_key) for membership in memberships], [("digest", "doi:10.1000/test")])
        self.assertIsNotNone(favorite)
        self.assertEqual(favorite.literature_item_key, "doi:10.1000/test")
        self.assertEqual(favorite.literature_item_id, item.id)
        self.assertIsNotNone(review)
        self.assertEqual(review.literature_item_key, "doi:10.1000/test")
        self.assertEqual(review.literature_item_id, item.id)
        self.assertEqual(review.review_final_decision, "keep")
        self.assertEqual(review.reviewer_notes, "keep this one")


if __name__ == "__main__":
    unittest.main()
