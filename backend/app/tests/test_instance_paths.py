from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

from app import database
from app.config import PROJECT_ROOT, get_settings, reset_settings_cache

TOOLS_DIR = PROJECT_ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from instance_paths import get_instance_paths


class InstancePathsTest(unittest.TestCase):
    def tearDown(self) -> None:
        for key in (
            "BIO_DIGEST_WEB_INSTANCE_ROOT",
            "BIO_DIGEST_PRODUCER_ROOT",
            "BIO_DIGEST_PRODUCER_ARCHIVE_DIR",
            "BIO_DIGEST_PRODUCER_EMAIL_CONFIG",
        ):
            os.environ.pop(key, None)
        database.engine = None
        database.SessionLocal = None
        reset_settings_cache()

    def test_default_paths_match_project_layout(self) -> None:
        paths = get_instance_paths(PROJECT_ROOT)
        expected_producer_root = PROJECT_ROOT.parent / "bio-literature-digest"
        self.assertEqual(paths.instance_root, PROJECT_ROOT / "bio-literature-config")
        self.assertEqual(
            paths.shared_data_dir,
            expected_producer_root / "bio-literature-config" / "data" / "shared",
        )
        self.assertEqual(paths.backend_env_file, PROJECT_ROOT / "bio-literature-config" / "env" / "web" / "backend.env.local")
        self.assertEqual(paths.producer_root, expected_producer_root)
        self.assertEqual(
            paths.producer_archive_dir,
            expected_producer_root / "archives" / "daily-digests",
        )

    def test_settings_resolve_relative_sqlite_path_inside_instance_data_dir(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bio-digest-web-instance-") as tmpdir:
            instance_root = Path(tmpdir)
            env_dir = instance_root / "env" / "web"
            env_dir.mkdir(parents=True)
            (env_dir / "backend.env.local").write_text(
                "\n".join(
                    [
                        "DATABASE_URL=sqlite:///./custom.db",
                        "SHARED_DATABASE_URL=sqlite:///./shared-custom.db",
                        "ACCESS_TRACE_DIR=access-traces",
                        "REVIEW_EXPORT_DIR=review-tables",
                        "SESSION_SECRET=test-secret",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            os.environ["BIO_DIGEST_WEB_INSTANCE_ROOT"] = str(instance_root)
            reset_settings_cache()
            settings = get_settings()
            self.assertEqual(settings.database_url, f"sqlite:///{(instance_root / 'data' / 'web' / 'custom.db').resolve()}")
            self.assertEqual(
                settings.shared_database_url,
                f"sqlite:///{(PROJECT_ROOT.parent / 'bio-literature-digest' / 'bio-literature-config' / 'data' / 'shared' / 'shared-custom.db').resolve()}",
            )
            self.assertEqual(settings.access_trace_dir, str((instance_root / "data" / "web" / "access-traces").resolve()))
            self.assertEqual(settings.review_export_dir, str((instance_root / "data" / "web" / "review-tables").resolve()))

    def test_configure_database_creates_instance_data_directory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="bio-digest-web-instance-db-") as tmpdir:
            instance_root = Path(tmpdir)
            env_dir = instance_root / "env" / "web"
            env_dir.mkdir(parents=True)
            (env_dir / "backend.env.local").write_text(
                "DATABASE_URL=sqlite:///./created-by-configure.db\nSESSION_SECRET=test-secret\n",
                encoding="utf-8",
            )
            os.environ["BIO_DIGEST_WEB_INSTANCE_ROOT"] = str(instance_root)
            reset_settings_cache()
            database.configure_database()
            expected_parent = instance_root / "data" / "web"
            self.assertTrue(expected_parent.exists())


if __name__ == "__main__":
    unittest.main()
