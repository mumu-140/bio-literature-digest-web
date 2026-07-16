from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

from fastapi.testclient import TestClient

from app import database
from app.config import reset_settings_cache


class DeerFlowSsoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="bio-digest-sso-")
        db_path = Path(self.tmpdir.name) / "api.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["INITIAL_ADMIN_EMAIL"] = "admin@example.com"
        os.environ["ACCESS_TRACE_DIR"] = str(Path(self.tmpdir.name) / "access-traces")
        os.environ["PRODUCER_SYNC_ENABLED"] = "false"
        os.environ["LITERATURE_API_BOOTSTRAP_TOKEN"] = "test-deerflow-sso-token"
        os.environ["LITERATURE_API_SCOPES"] = "literature:read,auth:sso"
        os.environ["WEB_BASE_URL"] = "https://accept.example.test"
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
            "ACCESS_TRACE_DIR",
            "PRODUCER_SYNC_ENABLED",
            "LITERATURE_API_BOOTSTRAP_TOKEN",
            "LITERATURE_API_SCOPES",
            "WEB_BASE_URL",
        ):
            os.environ.pop(key, None)
        database.engine = None
        database.SessionLocal = None
        reset_settings_cache()

    def _issue(self, client: TestClient, *, email: str = "reader@example.com"):
        return client.post(
            "/api/v1/auth/deerflow-sso",
            headers={"Authorization": "Bearer test-deerflow-sso-token"},
            json={
                "subject": "df-user-1",
                "email": email,
                "name": "Reader",
                "next_path": "/papers/published",
            },
        )

    def test_issue_auto_creates_user_and_consume_sets_session(self) -> None:
        with TestClient(self.app_factory()) as client:
            issued = self._issue(client)
            self.assertEqual(issued.status_code, 200)
            payload = issued.json()
            self.assertTrue(payload["created_user"])
            self.assertEqual(payload["expires_in"], 120)
            self.assertEqual(urlparse(payload["consume_url"]).path, "/api/auth/deerflow-sso/consume")

            consumed = client.post(
                "/api/auth/deerflow-sso/consume",
                data={"ticket": payload["ticket"], "next": "/papers/published"},
                follow_redirects=False,
            )
            self.assertEqual(consumed.status_code, 303)
            self.assertEqual(consumed.headers["location"], "/papers/published")
            self.assertIn("bio_digest_session=", consumed.headers["set-cookie"])

            me = client.get("/api/auth/me")
            self.assertEqual(me.status_code, 200)
            self.assertEqual(me.json()["email"], "reader@example.com")

    def test_ticket_is_one_time_and_existing_user_is_reused(self) -> None:
        with TestClient(self.app_factory()) as client:
            first = self._issue(client)
            self.assertEqual(first.status_code, 200)
            ticket = first.json()["ticket"]
            self.assertEqual(
                client.post(
                    "/api/auth/deerflow-sso/consume",
                    data={"ticket": ticket, "next": "/papers/published"},
                    follow_redirects=False,
                ).status_code,
                303,
            )
            replay = client.post(
                "/api/auth/deerflow-sso/consume",
                data={"ticket": ticket, "next": "/papers/published"},
                follow_redirects=False,
            )
            self.assertEqual(replay.status_code, 400)

            second = self._issue(client)
            self.assertEqual(second.status_code, 200)
            self.assertFalse(second.json()["created_user"])

    def test_scope_and_redirect_validation(self) -> None:
        with TestClient(self.app_factory()) as client:
            missing_auth = client.post(
                "/api/v1/auth/deerflow-sso",
                json={
                    "subject": "df-user-1",
                    "email": "reader@example.com",
                    "name": "Reader",
                    "next_path": "/papers/published",
                },
            )
            self.assertEqual(missing_auth.status_code, 401)

            issued = self._issue(client)
            consumed = client.post(
                "/api/auth/deerflow-sso/consume",
                data={"ticket": issued.json()["ticket"], "next": "https://evil.example/"},
                follow_redirects=False,
            )
            self.assertEqual(consumed.status_code, 303)
            self.assertEqual(consumed.headers["location"], "/papers/published")


if __name__ == "__main__":
    unittest.main()
