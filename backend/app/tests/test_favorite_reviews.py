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
from app.models import DigestRun, Favorite, Paper, PaperDailyEntry, User
from app.security import hash_password
from app.services.favorite_review_exports import build_user_review_records, build_weighted_review_records


class FavoriteReviewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="bio-digest-web-favorite-review-")
        db_path = Path(self.tmpdir.name) / "api.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["INITIAL_ADMIN_EMAIL"] = "admin@example.com"
        os.environ["INITIAL_ADMIN_PASSWORD"] = "ChangeMe123!"
        os.environ["REVIEW_EXPORT_DIR"] = str(Path(self.tmpdir.name) / "review-tables")
        reset_settings_cache()
        from app.main import create_app

        self.app_factory = create_app

    def tearDown(self) -> None:
        self.tmpdir.cleanup()
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("INITIAL_ADMIN_EMAIL", None)
        os.environ.pop("INITIAL_ADMIN_PASSWORD", None)
        os.environ.pop("REVIEW_EXPORT_DIR", None)
        reset_settings_cache()

    def _seed_paper(self) -> int:
        with database.SessionLocal() as db:
            digest_run = DigestRun(digest_date=date.fromisoformat("2026-04-06"), work_dir=str(Path(self.tmpdir.name) / "run"))
            db.add(digest_run)
            db.flush()
            paper = Paper(
                canonical_key="doi:10.1000/review-favorite",
                doi="10.1000/review-favorite",
                journal="Nature",
                category="omics",
                publish_date="2026-04-06T00:01:00Z",
                interest_level="感兴趣",
                interest_score=4,
                interest_tag="组学",
                title_en="Reviewable shared title",
                title_zh="可审核共享标题",
                summary_zh="摘要",
                abstract="abstract",
                article_url="https://example.org/review-favorite",
                tags_json=["omics", "plant"],
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
                    raw_record_json={
                        "source_id": "nature",
                        "llm_decision": "keep",
                        "llm_confidence": "0.91",
                        "llm_reason": "top journal",
                    },
                )
            )
            db.commit()
            return paper.id

    def test_patch_favorite_review_updates_review_fields(self) -> None:
        with TestClient(self.app_factory()) as client:
            login = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "ChangeMe123!"})
            self.assertEqual(login.status_code, 200)
            paper_id = self._seed_paper()
            create_favorite = client.post("/api/favorites", json={"paper_id": paper_id})
            self.assertEqual(create_favorite.status_code, 201)

            response = client.patch(
                f"/api/favorites/{paper_id}",
                json={
                    "review_interest_level": "非常感兴趣",
                    "review_interest_tag": "模型",
                    "review_final_decision": "review",
                    "review_final_category": "plant-biology",
                    "reviewer_notes": "需要人工二次看",
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["review_interest_level"], "非常感兴趣")
            self.assertEqual(payload["review_interest_tag"], "模型")
            self.assertEqual(payload["review_final_decision"], "review")
            self.assertEqual(payload["review_final_category"], "plant-biology")
            self.assertEqual(payload["reviewer_notes"], "需要人工二次看")
            self.assertIsNotNone(payload["review_updated_at"])

    def test_weighted_records_prefer_admin_vote_over_outsider(self) -> None:
        with TestClient(self.app_factory()) as client:
            login = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "ChangeMe123!"})
            self.assertEqual(login.status_code, 200)
            paper_id = self._seed_paper()

            with database.SessionLocal() as db:
                member = User(
                    email="member@example.com",
                    name="member",
                    password_hash=hash_password("ChangeMe123!"),
                    role="member",
                    is_active=True,
                    must_change_password=False,
                )
                outsider = User(
                    email="outsider@example.com",
                    name="outsider",
                    password_hash=hash_password("ChangeMe123!"),
                    role="member",
                    user_group="outsider",
                    owner_admin_user_id=1,
                    is_active=True,
                    must_change_password=False,
                )
                db.add_all([member, outsider])
                db.flush()
                db.add_all(
                    [
                        Favorite(
                            user_id=1,
                            paper_id=paper_id,
                            review_interest_level="非常感兴趣",
                            review_final_decision="keep",
                            review_final_category="plant-biology",
                            reviewer_notes="admin note",
                        ),
                        Favorite(
                            user_id=member.id,
                            paper_id=paper_id,
                            review_interest_level="一般",
                            review_final_decision="review",
                            review_final_category="omics",
                            reviewer_notes="member note",
                        ),
                        Favorite(
                            user_id=outsider.id,
                            paper_id=paper_id,
                            review_interest_level="仅保留",
                            review_final_decision="reject",
                            review_final_category="other",
                            reviewer_notes="outsider note",
                        ),
                    ]
                )
                db.flush()
                for favorite in db.scalars(select(Favorite)).all():
                    favorite.review_updated_at = favorite.favorited_at
                db.commit()

            with database.SessionLocal() as db:
                per_user = build_user_review_records(db)
                weighted = build_weighted_review_records(db)
            self.assertEqual(len(per_user), 3)
            self.assertEqual(len(weighted), 1)
            self.assertEqual(weighted[0]["interest_level"], "非常感兴趣")
            self.assertEqual(weighted[0]["review_final_decision"], "keep")
            self.assertEqual(weighted[0]["review_final_category"], "plant-biology")
            self.assertIn("contributors=", weighted[0]["reviewer_notes"])


if __name__ == "__main__":
    unittest.main()
