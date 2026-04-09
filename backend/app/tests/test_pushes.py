from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from app import database
from app.config import reset_settings_cache
from app.models import ImportedDigestMembership, ImportedDigestRun, ImportedLiteratureItem, User


class PushFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="bio-digest-web-pushes-")
        db_path = Path(self.tmpdir.name) / "api.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["INITIAL_ADMIN_EMAIL"] = "admin@example.com"
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
        os.environ.pop("PRODUCER_SYNC_ENABLED", None)
        database.engine = None
        database.SessionLocal = None
        reset_settings_cache()

    def _seed_imported_paper(self) -> int:
        with database.SessionLocal() as db:
            digest_run = ImportedDigestRun(
                digest_date=date.fromisoformat("2026-04-06"),
                source_run_id="run-1",
                source_updated_at_utc="2026-04-06T00:00:00Z",
            )
            db.add(digest_run)
            db.flush()
            paper = ImportedLiteratureItem(
                literature_item_key="doi:10.1000/push-flow",
                doi="10.1000/push-flow",
                canonical_url="https://example.org/push-flow",
                journal="Nature",
                category="omics",
                publish_date="2026-04-06T00:01:00Z",
                interest_level="感兴趣",
                interest_score=4,
                interest_tag="单细胞",
                title_en="Pushable title",
                title_zh="可推送标题",
                article_url="https://example.org/push-flow",
            )
            db.add(paper)
            db.flush()
            db.add(
                ImportedDigestMembership(
                    digest_run_id=digest_run.id,
                    literature_item_id=paper.id,
                    literature_item_key=paper.literature_item_key,
                    digest_date=date.fromisoformat("2026-04-06"),
                    list_type="digest",
                    publication_stage="journal",
                    row_index=1,
                    source_record_json={},
                )
            )
            db.commit()
            return paper.id

    def test_admin_push_uses_local_imported_item_and_recipient_can_mark_read(self) -> None:
        with TestClient(self.app_factory()) as admin_client:
            login = admin_client.post("/api/auth/login", json={"email": "admin@example.com"})
            self.assertEqual(login.status_code, 200)
            paper_id = self._seed_imported_paper()

            with database.SessionLocal() as db:
                recipient = User(
                    email="member@example.com",
                    name="Member",
                    password_hash="passwordless",
                    role="member",
                    is_active=True,
                )
                db.add(recipient)
                db.commit()
                db.refresh(recipient)
                recipient_id = recipient.id

            response = admin_client.post(
                "/api/admin/pushes",
                json={
                    "paper_id": paper_id,
                    "recipient_user_id": recipient_id,
                    "note": "please review locally",
                },
            )
            self.assertEqual(response.status_code, 201)
            payload = response.json()
            self.assertEqual(payload["paper_id"], paper_id)
            self.assertEqual(payload["canonical_key"], "doi:10.1000/push-flow")
            self.assertEqual(payload["recipient_user_id"], recipient_id)
            self.assertEqual(payload["title_en"], "Pushable title")
            self.assertFalse(payload["is_read"])

        with TestClient(self.app_factory()) as member_client:
            member_login = member_client.post("/api/auth/login", json={"email": "member@example.com"})
            self.assertEqual(member_login.status_code, 200)

            inbox = member_client.get("/api/pushes")
            self.assertEqual(inbox.status_code, 200)
            pushes = inbox.json()
            self.assertEqual(len(pushes), 1)
            self.assertEqual(pushes[0]["canonical_key"], "doi:10.1000/push-flow")
            self.assertEqual(pushes[0]["note"], "please review locally")
            push_id = pushes[0]["id"]

            mark_read = member_client.patch(f"/api/pushes/{push_id}", json={"is_read": True})
            self.assertEqual(mark_read.status_code, 200)
            self.assertTrue(mark_read.json()["is_read"])
