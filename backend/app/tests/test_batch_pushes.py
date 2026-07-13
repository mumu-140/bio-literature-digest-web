from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import select

from app import database
from app.config import reset_settings_cache
from app.models import (
    ActionLog,
    ImportedDigestMembership,
    ImportedDigestRun,
    ImportedLiteratureItem,
    LiteraturePushV2,
    User,
)


class BatchPushFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="bio-digest-web-batch-pushes-")
        db_path = Path(self.tmpdir.name) / "api.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["INITIAL_ADMIN_EMAIL"] = "admin@example.com"
        os.environ["PRODUCER_SYNC_ENABLED"] = "false"
        os.environ["PUSH_EMAIL_WORKER_ENABLED"] = "false"
        database.engine = None
        database.SessionLocal = None
        reset_settings_cache()
        from app.main import create_app

        self.app_factory = create_app

    def tearDown(self) -> None:
        self.tmpdir.cleanup()
        for key in (
            "DATABASE_URL",
            "INITIAL_ADMIN_EMAIL",
            "PRODUCER_SYNC_ENABLED",
            "PUSH_EMAIL_WORKER_ENABLED",
        ):
            os.environ.pop(key, None)
        database.engine = None
        database.SessionLocal = None
        reset_settings_cache()

    def _seed_imported_papers(self, count: int = 1) -> list[int]:
        with database.SessionLocal() as db:
            digest_run = ImportedDigestRun(
                digest_date=date.fromisoformat("2026-04-06"),
                source_run_id="run-1",
                source_updated_at_utc="2026-04-06T00:00:00Z",
            )
            db.add(digest_run)
            db.flush()
            paper_ids = [self._add_paper(db, digest_run, index) for index in range(count)]
            db.commit()
            return paper_ids

    def _add_paper(self, db, digest_run: ImportedDigestRun, index: int) -> int:
        suffix = "" if index == 0 else f"-{index + 1}"
        paper = ImportedLiteratureItem(
            literature_item_key="doi:10.1000/push-flow" + suffix,
            doi="10.1000/push-flow" + suffix,
            canonical_url="https://example.org/push-flow" + suffix,
            journal="Nature",
            category="omics",
            publish_date="2026-04-06T00:01:00Z",
            interest_level="感兴趣",
            interest_score=4,
            interest_tag="单细胞",
            title_en="Pushable title" + suffix,
            title_zh="可推送标题" + suffix,
            article_url="https://example.org/push-flow" + suffix,
        )
        db.add(paper)
        db.flush()
        db.add(ImportedDigestMembership(
            digest_run_id=digest_run.id,
            literature_item_id=paper.id,
            literature_item_key=paper.literature_item_key,
            digest_date=date.fromisoformat("2026-04-06"),
            list_type="digest",
            publication_stage="journal",
            row_index=index + 1,
            source_record_json={},
        ))
        return paper.id

    def _seed_users(self, count: int) -> list[int]:
        with database.SessionLocal() as db:
            users = [
                User(
                    email=f"member-{index}@example.com",
                    name=f"Member {index}",
                    password_hash="passwordless",
                    role="member",
                    is_active=True,
                )
                for index in range(count)
            ]
            db.add_all(users)
            db.commit()
            for user in users:
                db.refresh(user)
            return [user.id for user in users]

    def _login_admin(self, client: TestClient) -> int:
        response = client.post("/api/auth/login", json={"email": "admin@example.com"})
        self.assertEqual(response.status_code, 200)
        return response.json()["user"]["id"]

    def test_admin_can_batch_push_multiple_papers_to_multiple_users(self) -> None:
        with TestClient(self.app_factory()) as client:
            self._login_admin(client)
            response = client.post("/api/admin/pushes/batch", json={
                "paper_ids": self._seed_imported_papers(2),
                "recipient_user_ids": self._seed_users(3),
                "note": "review this batch",
                "send_email_notification": False,
            })
            self.assertEqual(response.status_code, 201)
            payload = response.json()
            self.assertEqual(
                (payload["paper_count"], payload["recipient_count"], payload["created_count"]),
                (2, 3, 6),
            )
            self.assertEqual(payload["email_queued_count"], 0)
            self.assertEqual(len(payload["items"]), 6)

        with database.SessionLocal() as db:
            pushes = list(db.scalars(select(LiteraturePushV2).where(
                LiteraturePushV2.batch_id == payload["batch_id"],
            )))
            logs = list(db.scalars(select(ActionLog).where(
                ActionLog.action_type == "admin_batch_push_papers",
            )))
            self.assertEqual(len(pushes), 6)
            self.assertEqual(len(logs), 3)
            self.assertEqual({log.detail_json["batch_id"] for log in logs}, {payload["batch_id"]})

    def test_batch_push_deduplicates_input_ids(self) -> None:
        with TestClient(self.app_factory()) as client:
            self._login_admin(client)
            paper_ids = self._seed_imported_papers(2)
            recipient_id = self._seed_users(1)[0]
            response = client.post("/api/admin/pushes/batch", json={
                "paper_ids": [paper_ids[0], paper_ids[0], paper_ids[1]],
                "recipient_user_ids": [recipient_id, recipient_id],
                "send_email_notification": False,
            })
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["created_count"], 2)

    def test_batch_push_rolls_back_when_any_paper_is_missing(self) -> None:
        with TestClient(self.app_factory()) as client:
            self._login_admin(client)
            response = client.post("/api/admin/pushes/batch", json={
                "paper_ids": [self._seed_imported_papers()[0], 999999],
                "recipient_user_ids": self._seed_users(1),
                "send_email_notification": False,
            })
            self.assertEqual(response.status_code, 404)
        self._assert_no_pushes()

    def test_batch_push_rejects_inactive_recipient_without_writes(self) -> None:
        with TestClient(self.app_factory()) as client:
            self._login_admin(client)
            recipient_id = self._seed_inactive_user()
            response = client.post("/api/admin/pushes/batch", json={
                "paper_ids": self._seed_imported_papers(),
                "recipient_user_ids": [recipient_id],
                "send_email_notification": False,
            })
            self.assertEqual(response.status_code, 422)
        self._assert_no_pushes()

    def test_batch_push_hides_outsider_owned_by_another_admin(self) -> None:
        with TestClient(self.app_factory()) as client:
            self._login_admin(client)
            recipient_id = self._seed_hidden_outsider()
            response = client.post("/api/admin/pushes/batch", json={
                "paper_ids": self._seed_imported_papers(),
                "recipient_user_ids": [recipient_id],
                "send_email_notification": False,
            })
            self.assertEqual(response.status_code, 404)
        self._assert_no_pushes()

    def test_batch_push_rejects_more_than_two_hundred_combinations(self) -> None:
        with TestClient(self.app_factory()) as client:
            self._login_admin(client)
            response = client.post("/api/admin/pushes/batch", json={
                "paper_ids": self._seed_imported_papers(15),
                "recipient_user_ids": self._seed_users(15),
                "send_email_notification": False,
            })
            self.assertEqual(response.status_code, 422)
            self.assertIn("200", response.json()["detail"])
        self._assert_no_pushes()

    def test_batch_push_rejects_empty_lists(self) -> None:
        with TestClient(self.app_factory()) as client:
            self._login_admin(client)
            response = client.post("/api/admin/pushes/batch", json={
                "paper_ids": [],
                "recipient_user_ids": [],
            })
            self.assertEqual(response.status_code, 422)

    def test_non_admin_cannot_batch_push(self) -> None:
        with TestClient(self.app_factory()) as client:
            self._login_admin(client)
            self._seed_users(1)
        with TestClient(self.app_factory()) as member_client:
            member_client.post("/api/auth/login", json={"email": "member-0@example.com"})
            response = member_client.post("/api/admin/pushes/batch", json={
                "paper_ids": [1],
                "recipient_user_ids": [1],
            })
            self.assertEqual(response.status_code, 403)

    def test_batch_email_worker_sends_one_summary_per_recipient(self) -> None:
        from app.services.push_email_queue import process_push_email_jobs

        with TestClient(self.app_factory()) as client:
            self._login_admin(client)
            response = client.post("/api/admin/pushes/batch", json={
                "paper_ids": self._seed_imported_papers(2),
                "recipient_user_ids": self._seed_users(2),
                "note": "summary please",
                "send_email_notification": True,
            })
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["email_queued_count"], 2)
            batch_id = response.json()["batch_id"]

        with database.SessionLocal() as db:
            with patch("app.services.push_email_queue.send_push_email_batch") as send:
                self.assertEqual(process_push_email_jobs(db), 4)
                self.assertEqual(send.call_count, 2)
                self.assertEqual(
                    sorted(len(call.kwargs["papers"]) for call in send.call_args_list),
                    [2, 2],
                )
            pushes = list(db.scalars(select(LiteraturePushV2).where(
                LiteraturePushV2.batch_id == batch_id,
            )))
            self.assertEqual({push.email_notification_status for push in pushes}, {"sent"})

    def _seed_inactive_user(self) -> int:
        with database.SessionLocal() as db:
            user = User(
                email="inactive@example.com",
                name="Inactive",
                password_hash="passwordless",
                role="member",
                is_active=False,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user.id

    def _seed_hidden_outsider(self) -> int:
        with database.SessionLocal() as db:
            owner = User(
                email="other-admin@example.com",
                name="Other Admin",
                password_hash="passwordless",
                role="admin",
                is_active=True,
            )
            db.add(owner)
            db.flush()
            outsider = User(
                email="hidden@example.com",
                name="Hidden",
                password_hash="passwordless",
                role="member",
                user_group="outsider",
                owner_admin_user_id=owner.id,
                is_active=True,
            )
            db.add(outsider)
            db.commit()
            db.refresh(outsider)
            return outsider.id

    def _assert_no_pushes(self) -> None:
        with database.SessionLocal() as db:
            self.assertEqual(len(list(db.scalars(select(LiteraturePushV2)))), 0)


if __name__ == "__main__":
    unittest.main()
