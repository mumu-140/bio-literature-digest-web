from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import yaml

from app.services.subscription_users import (
    SubscriptionEmailExistsError,
    add_subscription_email,
    remove_subscription_email,
    sync_subscription_email_status,
)


class SubscriptionUsersTest(unittest.TestCase):
    def test_adds_recipient_and_creates_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "local" / "integrations" / "users.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                yaml.safe_dump({"users": [{"uid": "UDI-0004", "email": "old@example.com"}]}),
                encoding="utf-8",
            )

            result = add_subscription_email(
                config_path,
                email="New@Example.com",
                name="New User",
                user_group="internal",
            )

            payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            created = payload["users"][-1]
            self.assertEqual(result.uid, "UDI-0005")
            self.assertEqual(created["email"], "new@example.com")
            self.assertTrue(created["receives_digest"])
            self.assertTrue(Path(result.backup_path).exists())

    def test_rejects_duplicate_without_rewriting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "local" / "integrations" / "users.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                yaml.safe_dump({"users": [{"uid": "UDI-0001", "email": "same@example.com"}]}),
                encoding="utf-8",
            )
            original = config_path.read_bytes()

            with self.assertRaises(SubscriptionEmailExistsError):
                add_subscription_email(
                    config_path,
                    email="SAME@example.com",
                    name="Duplicate",
                    user_group="internal",
                )

            self.assertEqual(config_path.read_bytes(), original)

    def test_removes_and_syncs_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "local" / "integrations" / "users.yaml"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                yaml.safe_dump(
                    {
                        "users": [
                            {"uid": "UDI-0001", "email": "keep@example.com", "is_active": True},
                            {"uid": "UDI-0002", "email": "drop@example.com", "is_active": True},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            self.assertTrue(sync_subscription_email_status(config_path, email="KEEP@example.com", is_active=False))
            self.assertTrue(remove_subscription_email(config_path, email="DROP@example.com"))
            payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["users"]), 1)
            self.assertEqual(payload["users"][0]["email"], "keep@example.com")
            self.assertFalse(payload["users"][0]["is_active"])
