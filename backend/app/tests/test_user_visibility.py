from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import reset_settings_cache


class UserVisibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="bio-digest-web-visibility-")
        db_path = Path(self.tmpdir.name) / "visibility.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["INITIAL_ADMIN_EMAIL"] = "primary-admin@example.com"
        os.environ["INITIAL_ADMIN_PASSWORD"] = "ChangeMe123!"
        os.environ["ACCESS_TRACE_DIR"] = str(Path(self.tmpdir.name) / "access-traces")
        reset_settings_cache()
        from app.main import create_app

        self.app_factory = create_app

    def tearDown(self) -> None:
        self.tmpdir.cleanup()
        for key in ("DATABASE_URL", "INITIAL_ADMIN_EMAIL", "INITIAL_ADMIN_PASSWORD", "ACCESS_TRACE_DIR"):
            os.environ.pop(key, None)
        reset_settings_cache()

    def _login(self, email: str, password: str) -> dict[str, str]:
        response = self.client.post("/api/auth/login", json={"email": email, "password": password})
        self.assertEqual(response.status_code, 200)
        return response.cookies

    def test_outsider_user_visible_only_to_owner_admin(self) -> None:
        with TestClient(self.app_factory()) as client:
            self.client = client
            primary = self._login("primary-admin@example.com", "ChangeMe123!")

            create_admin = self.client.post(
                "/api/admin/users",
                json={"email": "secondary-admin@example.com", "name": "", "password": "ChangeMe123!", "role": "admin", "user_group": "internal"},
                cookies=primary,
            )
            self.assertEqual(create_admin.status_code, 201)

            create_outsider = self.client.post(
                "/api/admin/users",
                json={"email": "outsider@example.com", "name": "", "password": "ChangeMe123!", "role": "member", "user_group": "outsider"},
                cookies=primary,
            )
            self.assertEqual(create_outsider.status_code, 201)
            outsider_id = create_outsider.json()["id"]
            self.assertEqual(create_outsider.json()["owner_admin_user_id"], 1)

            secondary = self._login("secondary-admin@example.com", "ChangeMe123!")

            visible_to_primary = self.client.get("/api/admin/users", cookies=primary)
            self.assertEqual(visible_to_primary.status_code, 200)
            self.assertIn("outsider@example.com", [user["email"] for user in visible_to_primary.json()])

            visible_to_secondary = self.client.get("/api/admin/users", cookies=secondary)
            self.assertEqual(visible_to_secondary.status_code, 200)
            self.assertNotIn("outsider@example.com", [user["email"] for user in visible_to_secondary.json()])

            hidden_reset = self.client.post(
                f"/api/admin/users/{outsider_id}/reset-password",
                json={"password": "AnotherPass123!"},
                cookies=secondary,
            )
            self.assertEqual(hidden_reset.status_code, 404)


if __name__ == "__main__":
    unittest.main()
