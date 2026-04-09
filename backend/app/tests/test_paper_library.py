from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from app import database
from app.config import reset_settings_cache
from app.models import ImportedDigestMembership, ImportedDigestRun, ImportedLiteratureItem


class PaperLibraryApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="bio-digest-web-library-")
        db_path = Path(self.tmpdir.name) / "library.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["INITIAL_ADMIN_EMAIL"] = "admin@example.com"
        os.environ["ACCESS_TRACE_DIR"] = str(Path(self.tmpdir.name) / "access-traces")
        os.environ["PRODUCER_SYNC_ENABLED"] = "false"
        database.engine = None
        database.SessionLocal = None
        reset_settings_cache()
        from app.main import create_app

        self.app_factory = create_app

    def tearDown(self) -> None:
        self.tmpdir.cleanup()
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("INITIAL_ADMIN_EMAIL", None)
        os.environ.pop("ACCESS_TRACE_DIR", None)
        os.environ.pop("PRODUCER_SYNC_ENABLED", None)
        database.engine = None
        database.SessionLocal = None
        reset_settings_cache()

    def _seed_papers(self) -> None:
        with database.SessionLocal() as db:
            run_0909 = ImportedDigestRun(
                digest_date=date.fromisoformat("2026-04-09"),
                source_run_id="run-0909",
                source_updated_at_utc="2026-04-09T00:00:00Z",
            )
            run_0908 = ImportedDigestRun(
                digest_date=date.fromisoformat("2026-04-08"),
                source_run_id="run-0908",
                source_updated_at_utc="2026-04-08T00:00:00Z",
            )
            run_0407 = ImportedDigestRun(
                digest_date=date.fromisoformat("2026-04-07"),
                source_run_id="run-0407",
                source_updated_at_utc="2026-04-07T00:00:00Z",
            )
            db.add_all([run_0909, run_0908, run_0407])
            db.flush()

            paper_a = ImportedLiteratureItem(
                literature_item_key="doi:10.1000/a",
                doi="10.1000/a",
                canonical_url="https://example.org/a",
                article_url="https://example.org/a",
                journal="Nature",
                category="omics",
                publish_date="2026-04-09T13:00:00Z",
                interest_level="非常感兴趣",
                interest_score=5,
                interest_tag="单细胞",
                title_en="Paper A",
                title_zh="论文 A",
            )
            paper_b = ImportedLiteratureItem(
                literature_item_key="doi:10.1000/b",
                doi="10.1000/b",
                canonical_url="https://example.org/b",
                article_url="https://example.org/b",
                journal="Cell",
                category="therapy",
                publish_date="2026-04-08",
                interest_level="感兴趣",
                interest_score=4,
                interest_tag="免疫",
                title_en="Paper B",
                title_zh="论文 B",
            )
            paper_c = ImportedLiteratureItem(
                literature_item_key="doi:10.1000/c",
                doi="10.1000/c",
                canonical_url="https://example.org/c",
                article_url="https://example.org/c",
                journal="Science",
                category="tools",
                publish_date="2026-04-07T05:45:00Z",
                interest_level="一般",
                interest_score=3,
                interest_tag="平台",
                title_en="Paper C",
                title_zh="论文 C",
            )
            paper_d = ImportedLiteratureItem(
                literature_item_key="doi:10.1000/d",
                doi="10.1000/d",
                canonical_url="https://example.org/d",
                article_url="https://example.org/d",
                journal="Cell",
                category="tools",
                publish_date="2026-04-09T09:15:00Z",
                interest_level="感兴趣",
                interest_score=4,
                interest_tag="平台",
                title_en="Paper D",
                title_zh="论文 D",
            )
            paper_e = ImportedLiteratureItem(
                literature_item_key="doi:10.1000/e",
                doi="10.1000/e",
                canonical_url="https://example.org/e",
                article_url="https://example.org/e",
                journal="Science",
                category="tools",
                publish_date="2026-04-09T08:45:00Z",
                interest_level="一般",
                interest_score=3,
                interest_tag="结构",
                title_en="Paper E",
                title_zh="论文 E",
            )
            paper_f = ImportedLiteratureItem(
                literature_item_key="doi:10.1000/f",
                doi="10.1000/f",
                canonical_url="https://example.org/f",
                article_url="https://example.org/f",
                journal="The Lancet",
                category="therapy",
                publish_date="2026-04-09T07:00:00Z",
                interest_level="非常感兴趣",
                interest_score=5,
                interest_tag="临床",
                title_en="Paper F",
                title_zh="论文 F",
            )
            db.add_all([paper_a, paper_b, paper_c, paper_d, paper_e, paper_f])
            db.flush()

            db.add_all(
                [
                    ImportedDigestMembership(
                        digest_run_id=run_0909.id,
                        literature_item_id=paper_a.id,
                        literature_item_key=paper_a.literature_item_key,
                        digest_date=date.fromisoformat("2026-04-09"),
                        list_type="digest",
                        publication_stage="journal",
                        row_index=1,
                        source_record_json={},
                    ),
                    ImportedDigestMembership(
                        digest_run_id=run_0908.id,
                        literature_item_id=paper_a.id,
                        literature_item_key=paper_a.literature_item_key,
                        digest_date=date.fromisoformat("2026-04-08"),
                        list_type="digest",
                        publication_stage="journal",
                        row_index=2,
                        source_record_json={},
                    ),
                    ImportedDigestMembership(
                        digest_run_id=run_0909.id,
                        literature_item_id=paper_b.id,
                        literature_item_key=paper_b.literature_item_key,
                        digest_date=date.fromisoformat("2026-04-09"),
                        list_type="digest",
                        publication_stage="journal",
                        row_index=3,
                        source_record_json={},
                    ),
                    ImportedDigestMembership(
                        digest_run_id=run_0407.id,
                        literature_item_id=paper_c.id,
                        literature_item_key=paper_c.literature_item_key,
                        digest_date=date.fromisoformat("2026-04-07"),
                        list_type="digest",
                        publication_stage="journal",
                        row_index=1,
                        source_record_json={},
                    ),
                    ImportedDigestMembership(
                        digest_run_id=run_0909.id,
                        literature_item_id=paper_d.id,
                        literature_item_key=paper_d.literature_item_key,
                        digest_date=date.fromisoformat("2026-04-09"),
                        list_type="digest",
                        publication_stage="journal",
                        row_index=4,
                        source_record_json={},
                    ),
                    ImportedDigestMembership(
                        digest_run_id=run_0909.id,
                        literature_item_id=paper_e.id,
                        literature_item_key=paper_e.literature_item_key,
                        digest_date=date.fromisoformat("2026-04-09"),
                        list_type="digest",
                        publication_stage="journal",
                        row_index=5,
                        source_record_json={},
                    ),
                    ImportedDigestMembership(
                        digest_run_id=run_0909.id,
                        literature_item_id=paper_f.id,
                        literature_item_key=paper_f.literature_item_key,
                        digest_date=date.fromisoformat("2026-04-09"),
                        list_type="digest",
                        publication_stage="journal",
                        row_index=6,
                        source_record_json={},
                    ),
                ]
            )
            db.commit()

    def test_library_overview_groups_by_publish_date(self) -> None:
        with TestClient(self.app_factory()) as client:
            login = client.post("/api/auth/login", json={"email": "admin@example.com"})
            self.assertEqual(login.status_code, 200)
            self._seed_papers()

            response = client.get("/api/papers/library?initial_group_count=2")
            self.assertEqual(response.status_code, 200)
            payload = response.json()

            self.assertEqual(payload["total_papers"], 6)
            self.assertEqual(
                [group["publish_date"] for group in payload["groups"]],
                ["2026-04-09", "2026-04-08", "2026-04-07"],
            )
            self.assertEqual(
                [group["publish_date"] for group in payload["loaded_groups"]],
                ["2026-04-09", "2026-04-08"],
            )
            self.assertEqual(payload["available_publish_dates"], ["2026-04-09", "2026-04-08", "2026-04-07"])
            self.assertEqual(payload["loaded_groups"][0]["items"][0]["digest_date"], "2026-04-09")
            self.assertEqual(payload["loaded_groups"][0]["items"][0]["publish_date_day"], "2026-04-09")
            self.assertEqual(
                [item["journal"] for item in payload["loaded_groups"][0]["items"][:4]],
                ["Cell", "Nature", "Science", "The Lancet"],
            )
            self.assertEqual(payload["loaded_groups"][1]["items"][0]["publish_date_day"], "2026-04-08")

    def test_library_group_endpoint_returns_requested_publish_date(self) -> None:
        with TestClient(self.app_factory()) as client:
            login = client.post("/api/auth/login", json={"email": "admin@example.com"})
            self.assertEqual(login.status_code, 200)
            self._seed_papers()

            overview = client.get("/api/papers/library?sort=publish_date_asc&initial_group_count=1")
            self.assertEqual(overview.status_code, 200)
            self.assertEqual(overview.json()["groups"][0]["publish_date"], "2026-04-07")

            response = client.get("/api/papers/library/groups/2026-04-08")
            self.assertEqual(response.status_code, 200)
            payload = response.json()

            self.assertEqual(payload["publish_date"], "2026-04-08")
            self.assertEqual(payload["paper_count"], 1)
            self.assertEqual(payload["items"][0]["title_en"], "Paper B")
            self.assertEqual(payload["items"][0]["publish_date_day"], "2026-04-08")


if __name__ == "__main__":
    unittest.main()
