from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from app import database
from app.config import reset_settings_cache
from app.models import DigestRun, Paper, PaperDailyEntry
from app.security import create_email_login_token


class AuthAndFavoritesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="bio-digest-web-api-")
        db_path = Path(self.tmpdir.name) / "api.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["INITIAL_ADMIN_EMAIL"] = "admin@example.com"
        os.environ["INITIAL_ADMIN_PASSWORD"] = "ChangeMe123!"
        os.environ["ACCESS_TRACE_DIR"] = str(Path(self.tmpdir.name) / "access-traces")
        reset_settings_cache()
        self.app_factory = None
        from app.main import create_app

        self.app_factory = create_app

    def tearDown(self) -> None:
        self.tmpdir.cleanup()
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("INITIAL_ADMIN_EMAIL", None)
        os.environ.pop("INITIAL_ADMIN_PASSWORD", None)
        os.environ.pop("ACCESS_TRACE_DIR", None)
        reset_settings_cache()

    def test_admin_login(self) -> None:
        with TestClient(self.app_factory()) as client:
            response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "ChangeMe123!"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["user"]["role"], "admin")
            self.assertEqual(response.json()["user"]["session_auth_method"], "password")

    def test_email_login_allows_first_password_change_without_current_password(self) -> None:
        with TestClient(self.app_factory()) as client:
            token, _ = create_email_login_token("admin@example.com")
            response = client.post("/api/auth/email-login", json={"email": "admin@example.com", "password": token})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["user"]["session_auth_method"], "email_link")

            me = client.get("/api/auth/me")
            self.assertEqual(me.status_code, 200)
            self.assertEqual(me.json()["session_auth_method"], "email_link")

            change = client.post(
                "/api/auth/change-password",
                json={"current_password": "", "new_password": "NewPassword123!"},
            )
            self.assertEqual(change.status_code, 200)
            self.assertFalse(change.json()["must_change_password"])

            login = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "NewPassword123!"})
            self.assertEqual(login.status_code, 200)

    def test_favorite_reuses_shared_paper_metadata(self) -> None:
        with TestClient(self.app_factory()) as client:
            login = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "ChangeMe123!"})
            self.assertEqual(login.status_code, 200)

            with database.SessionLocal() as db:
                digest_run = DigestRun(digest_date=date.fromisoformat("2026-04-06"), work_dir=str(Path(self.tmpdir.name) / "run"))
                db.add(digest_run)
                db.flush()
                paper = Paper(
                    canonical_key="doi:10.1000/shared",
                    doi="10.1000/shared",
                    journal="Nature",
                    category="omics",
                    publish_date="2026-04-06T00:01:00Z",
                    interest_level="感兴趣",
                    interest_score=4,
                    interest_tag="单细胞",
                    title_en="Original title",
                    title_zh="原标题",
                    article_url="https://example.org/shared",
                )
                db.add(paper)
                db.flush()
                db.add(
                    PaperDailyEntry(
                        digest_run_id=digest_run.id,
                        paper_id=paper.id,
                        digest_date=date.fromisoformat("2026-04-06"),
                        publication_stage="journal",
                        row_index=1,
                        raw_record_json={},
                    )
                )
                db.commit()
                paper_id = paper.id

            create_first = client.post("/api/favorites", json={"paper_id": paper_id})
            self.assertEqual(create_first.status_code, 201)
            create_second = client.post("/api/favorites", json={"paper_id": paper_id})
            self.assertEqual(create_second.status_code, 201)
            self.assertEqual(create_first.json()["id"], create_second.json()["id"])

            with database.SessionLocal() as db:
                paper = db.get(Paper, paper_id)
                paper.title_en = "Updated shared title"
                db.commit()

            favorites = client.get("/api/favorites")
            self.assertEqual(favorites.status_code, 200)
            self.assertEqual(len(favorites.json()), 1)
            self.assertEqual(favorites.json()[0]["title_en"], "Updated shared title")


if __name__ == "__main__":
    unittest.main()
