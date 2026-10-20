"""OTP login and whitelist behavior tests."""

from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from app import database
from app.config import reset_settings_cache
from app.models import LoginOtpCode, User


def _request_code(client: TestClient, email: str = "admin@example.com") -> dict:
    response = client.post("/api/auth/login/otp/request", json={"email": email})
    assert response.status_code == 202, response.text
    return response.json()


def _latest_otp(db, email: str) -> LoginOtpCode:
    otp = (
        db.query(LoginOtpCode)
        .filter(LoginOtpCode.email == email)
        .order_by(LoginOtpCode.created_at.desc())
        .first()
    )
    assert otp is not None
    return otp


class LoginOtpTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="bio-digest-web-otp-")
        db_path = Path(self.tmpdir.name) / "otp.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["INITIAL_ADMIN_EMAIL"] = "admin@example.com"
        os.environ["ACCESS_TRACE_DIR"] = str(Path(self.tmpdir.name) / "access-traces")
        os.environ["PRODUCER_SYNC_ENABLED"] = "false"
        os.environ["OTP_LOGIN_ENABLED"] = "true"
        os.environ["OTP_DEV_ECHO"] = "true"
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
            "OTP_LOGIN_ENABLED",
            "OTP_DEV_ECHO",
            "OTP_RESEND_COOLDOWN_SECONDS",
            "OTP_PER_EMAIL_HOURLY_LIMIT",
        ):
            os.environ.pop(key, None)
        database.engine = None
        database.SessionLocal = None
        reset_settings_cache()

    def test_login_endpoint_returns_issued_payload(self) -> None:
        with TestClient(self.app_factory()) as client:
            response = client.post("/api/auth/login", json={"email": "admin@example.com"})
            self.assertEqual(response.status_code, 202)
            body = response.json()
            self.assertEqual(body["email"], "admin@example.com")
            self.assertEqual(body["expires_in"], 600)
            self.assertEqual(body["resend_after"], 60)
            self.assertIn("dev_code", body)
            self.assertIn("Cache-Control", response.headers)

    def test_verify_with_dev_echo_code_sets_session_cookie(self) -> None:
        with TestClient(self.app_factory()) as client:
            issued = _request_code(client)
            self.assertTrue(issued["dev_code"])
            with database.SessionLocal() as db:
                otp = _latest_otp(db, "admin@example.com")
                self.assertIsNone(otp.consumed_at)
                self.assertEqual(otp.attempts_remaining, 5)

            verify = client.post(
                "/api/auth/login/otp/verify",
                json={"email": "admin@example.com", "code": issued["dev_code"]},
            )
            self.assertEqual(verify.status_code, 200)
            self.assertEqual(verify.json()["user"]["email"], "admin@example.com")
            self.assertIn("bio_digest_session", verify.cookies)

            me = client.get("/api/auth/me")
            self.assertEqual(me.status_code, 200)
            self.assertEqual(me.json()["email"], "admin@example.com")

            with database.SessionLocal() as db:
                otp = _latest_otp(db, "admin@example.com")
                self.assertIsNotNone(otp.consumed_at)

    def test_wrong_code_decrements_attempts(self) -> None:
        with TestClient(self.app_factory()) as client:
            issued = _request_code(client)
            bad = client.post(
                "/api/auth/login/otp/verify",
                json={"email": "admin@example.com", "code": "000000" if issued["dev_code"] != "000000" else "111111"},
            )
            self.assertEqual(bad.status_code, 400)
            self.assertIn("还可尝试", bad.json()["detail"])

            with database.SessionLocal() as db:
                otp = _latest_otp(db, "admin@example.com")
                self.assertEqual(otp.attempts_remaining, 4)

    def test_resend_within_cooldown_is_429(self) -> None:
        with TestClient(self.app_factory()) as client:
            first = _request_code(client)
            second = client.post("/api/auth/login/otp/request", json={"email": "admin@example.com"})
            self.assertEqual(second.status_code, 429)
            self.assertIn("频繁", second.json()["detail"])

    def test_unknown_email_gets_indistinguishable_response_and_no_email(self) -> None:
        with TestClient(self.app_factory()) as client:
            response = client.post("/api/auth/login/otp/request", json={"email": "ghost@example.com"})
            self.assertEqual(response.status_code, 202)
            body = response.json()
            self.assertIsNone(body.get("dev_code"))

            verify = client.post(
                "/api/auth/login/otp/verify",
                json={"email": "ghost@example.com", "code": "123456"},
            )
            self.assertEqual(verify.status_code, 403)
            self.assertIn("未开通访问权限", verify.json()["detail"])

            with database.SessionLocal() as db:
                self.assertEqual(db.query(LoginOtpCode).filter(LoginOtpCode.email == "ghost@example.com").count(), 0)
                self.assertIsNone(db.query(User).filter(User.email == "ghost@example.com").first())

    def test_legacy_direct_login_still_available_when_otp_disabled(self) -> None:
        os.environ["OTP_LOGIN_ENABLED"] = "false"
        database.engine = None
        database.SessionLocal = None
        reset_settings_cache()
        with TestClient(self.app_factory()) as client:
            response = client.post("/api/auth/login", json={"email": "admin@example.com"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["user"]["email"], "admin@example.com")
            self.assertIn("bio_digest_session", response.cookies)

    def test_inactive_user_cannot_request_or_verify(self) -> None:
        with TestClient(self.app_factory()) as client:
            with database.SessionLocal() as db:
                db.add(
                    User(
                        email="frozen@example.com",
                        name="Frozen",
                        role="member",
                        user_group="internal",
                        is_active=False,
                    )
                )
                db.commit()

            request = client.post("/api/auth/login/otp/request", json={"email": "frozen@example.com"})
            self.assertEqual(request.status_code, 403)

            # Seed a code directly, then ensure verify refuses inactive accounts.
            with database.SessionLocal() as db:
                db.add(
                    LoginOtpCode(
                        email="frozen@example.com",
                        code_hash=hashlib_sha256("frozen@example.com:123456"),
                        attempts_remaining=5,
                        expires_at=datetime.utcnow() + timedelta(minutes=10),
                    )
                )
                db.commit()

            verify = client.post(
                "/api/auth/login/otp/verify",
                json={"email": "frozen@example.com", "code": "123456"},
            )
            self.assertEqual(verify.status_code, 403)


def hashlib_sha256(value: str) -> str:
    import hashlib

    secret = os.environ.get("SESSION_SECRET", "change-me")
    return hashlib.sha256(f"{secret}:{value}".encode("utf-8")).hexdigest()


if __name__ == "__main__":
    unittest.main()
