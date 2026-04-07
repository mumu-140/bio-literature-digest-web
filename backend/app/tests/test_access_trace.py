from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi import Request

from app.config import reset_settings_cache
from app.models import User
from app.services.access_trace import write_access_trace


class AccessTraceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="bio-digest-web-access-trace-")
        os.environ["ACCESS_TRACE_DIR"] = str(Path(self.tmpdir.name) / "traces")
        reset_settings_cache()

    def tearDown(self) -> None:
        self.tmpdir.cleanup()
        os.environ.pop("ACCESS_TRACE_DIR", None)
        reset_settings_cache()

    def test_write_access_trace_creates_append_only_file(self) -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/auth/me",
            "query_string": b"",
            "headers": [
                (b"host", b"app.example.com"),
                (b"user-agent", b"pytest"),
                (b"cf-connecting-ip", b"203.0.113.8"),
                (b"cf-ipcountry", b"US"),
                (b"x-browser-timezone", b"Asia/Shanghai"),
            ],
            "client": ("127.0.0.1", 50000),
            "scheme": "https",
            "server": ("app.example.com", 443),
        }
        request = Request(scope)
        user = User(id=7, email="trace@example.com", name="Trace", password_hash="hashed", role="member")

        first_path = write_access_trace(user=user, request=request, event_type="session_entry")
        second_path = write_access_trace(user=user, request=request, event_type="session_entry")

        self.assertTrue(first_path.exists())
        self.assertTrue(second_path.exists())
        self.assertNotEqual(first_path, second_path)
        payload = json.loads(first_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["user"]["email"], "trace@example.com")
        self.assertEqual(payload["request"]["ip"]["cf_connecting_ip"], "203.0.113.8")
        self.assertEqual(payload["request"]["location"]["timezone"], "Asia/Shanghai")


if __name__ == "__main__":
    unittest.main()
