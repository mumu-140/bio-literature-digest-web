from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import select

from app import database
from app.models import ActionLog, User
from app.services.user_sync import read_recipient_emails, sync_users_from_email_config


class UserSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="bio-digest-web-user-sync-")
        self.root = Path(self.tmpdir.name)
        database.configure_database(f"sqlite:///{self.root / 'test.db'}")
        database.Base.metadata.create_all(bind=database.engine)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_read_recipient_emails_ignores_disabled_profiles(self) -> None:
        config_path = self.root / "email_config.local.yaml"
        config_path.write_text(
            "\n".join(
                [
                    "smtp_profiles:",
                    "  qq_mail:",
                    "    enabled: true",
                    "    to_emails:",
                    "      - admin@example.com",
                    "      - member@example.com",
                    "  disabled_profile:",
                    "    enabled: false",
                    "    to_emails:",
                    "      - skipped@example.com",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        self.assertEqual(read_recipient_emails(config_path), ["admin@example.com", "member@example.com"])

    def test_sync_users_from_email_config_is_idempotent(self) -> None:
        config_path = self.root / "email_config.local.yaml"
        config_path.write_text(
            "\n".join(
                [
                    "smtp_profiles:",
                    "  qq_mail:",
                    "    enabled: true",
                    "    to_emails:",
                    "      - first@example.com",
                    "      - second@example.com",
                    "      - first@example.com",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        with database.SessionLocal() as db:
            first = sync_users_from_email_config(db, config_path=config_path)
        self.assertEqual([user.email for user in first.created], ["first@example.com", "second@example.com"])

        with database.SessionLocal() as db:
            second = sync_users_from_email_config(db, config_path=config_path)
            users = list(db.scalars(select(User).order_by(User.email.asc())))
            logs = list(db.scalars(select(ActionLog).order_by(ActionLog.id.asc())))

        self.assertEqual([user.email for user in second.created], [])
        self.assertEqual([user.email for user in second.existing], ["first@example.com", "second@example.com"])
        self.assertEqual([user.email for user in users], ["first@example.com", "second@example.com"])
        self.assertEqual([user.must_change_password for user in users], [False, False])
        self.assertEqual([log.action_type for log in logs], ["sync_email_recipient_create_user", "sync_email_recipient_create_user"])


if __name__ == "__main__":
    unittest.main()
