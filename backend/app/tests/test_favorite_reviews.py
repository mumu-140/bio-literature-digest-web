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
from app.models import (
    ImportedDigestMembership,
    ImportedDigestRun,
    ImportedLiteratureItem,
    User,
    UserLiteratureFavorite,
    UserManualReview,
)
from app.services.favorite_review_exports import _user_review_stem, build_user_review_records, build_weighted_review_records


class FavoriteReviewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="bio-digest-web-favorite-review-")
        db_path = Path(self.tmpdir.name) / "api.db"
        producer_root = Path(self.tmpdir.name) / "producer"
        rules_path = producer_root / "config" / "content" / "category_rules.yaml"
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        rules_path.write_text(
            """
categories:
  gene-function-regulation: {}
  omics: {}
interest_profile:
  levels:
    - label: 一般
      score: 3
    - label: 感兴趣
      score: 4
interest_tag_taxonomy:
  labels:
    - 基因研究
    - 组学
""".strip(),
            encoding="utf-8",
        )
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        os.environ["INITIAL_ADMIN_EMAIL"] = "admin@example.com"
        os.environ["REVIEW_EXPORT_DIR"] = str(Path(self.tmpdir.name) / "review-tables")
        os.environ["PRODUCER_SYNC_ENABLED"] = "false"
        os.environ["PRODUCER_ROOT"] = str(producer_root)
        database.engine = None
        database.SessionLocal = None
        reset_settings_cache()
        from app.main import create_app

        self.app_factory = create_app

    def tearDown(self) -> None:
        self.tmpdir.cleanup()
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("INITIAL_ADMIN_EMAIL", None)
        os.environ.pop("REVIEW_EXPORT_DIR", None)
        os.environ.pop("PRODUCER_SYNC_ENABLED", None)
        os.environ.pop("PRODUCER_ROOT", None)
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
                literature_item_key="doi:10.1000/review-favorite",
                doi="10.1000/review-favorite",
                journal="Nature",
                category="omics",
                publish_date="2026-04-06T00:01:00Z",
                interest_level="感兴趣",
                interest_score=4,
                interest_tag="组学",
                title_en="Reviewable imported title",
                title_zh="可审核导入标题",
                summary_zh="摘要",
                abstract="abstract",
                article_url="https://example.org/review-favorite",
                tags_json=["omics", "plant"],
                source_id="nature",
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
                    source_record_json={
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
            login = client.post("/api/auth/login", json={"email": "admin@example.com"})
            self.assertEqual(login.status_code, 200)
            paper_id = self._seed_imported_paper()
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
            self.assertEqual(payload["canonical_key"], "doi:10.1000/review-favorite")

    def test_review_options_follow_current_producer_rules_location(self) -> None:
        with TestClient(self.app_factory()) as client:
            login = client.post("/api/auth/login", json={"email": "admin@example.com"})
            self.assertEqual(login.status_code, 200)

            response = client.get("/api/favorites/review-options")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["interest_levels"], ["一般", "感兴趣"])
            self.assertEqual(payload["interest_tags"], ["基因研究", "组学"])
            self.assertEqual(payload["review_final_decisions"], ["keep", "review", "reject"])
            self.assertEqual(payload["review_final_categories"], ["gene-function-regulation", "omics"])

    def test_weighted_records_prefer_admin_vote_over_outsider(self) -> None:
        with TestClient(self.app_factory()):
            pass
        paper_id = self._seed_imported_paper()

        with database.SessionLocal() as db:
            admin = db.scalar(select(User).where(User.email == "admin@example.com"))
            member = User(
                email="member@example.com",
                name="member",
                password_hash="passwordless",
                role="member",
                is_active=True,
            )
            outsider = User(
                email="outsider@example.com",
                name="outsider",
                password_hash="passwordless",
                role="member",
                user_group="outsider",
                owner_admin_user_id=admin.id,
                is_active=True,
            )
            db.add_all([member, outsider])
            db.flush()
            paper = db.get(ImportedLiteratureItem, paper_id)
            db.add_all(
                [
                    UserLiteratureFavorite(user_id=admin.id, literature_item_id=paper.id, literature_item_key=paper.literature_item_key),
                    UserLiteratureFavorite(user_id=member.id, literature_item_id=paper.id, literature_item_key=paper.literature_item_key),
                    UserLiteratureFavorite(user_id=outsider.id, literature_item_id=paper.id, literature_item_key=paper.literature_item_key),
                    UserManualReview(
                        user_id=admin.id,
                        literature_item_id=paper.id,
                        literature_item_key=paper.literature_item_key,
                        review_interest_level="非常感兴趣",
                        review_final_decision="keep",
                        review_final_category="plant-biology",
                        reviewer_notes="admin note",
                    ),
                    UserManualReview(
                        user_id=member.id,
                        literature_item_id=paper.id,
                        literature_item_key=paper.literature_item_key,
                        review_interest_level="一般",
                        review_final_decision="review",
                        review_final_category="omics",
                        reviewer_notes="member note",
                    ),
                    UserManualReview(
                        user_id=outsider.id,
                        literature_item_id=paper.id,
                        literature_item_key=paper.literature_item_key,
                        review_interest_level="仅保留",
                        review_final_decision="reject",
                        review_final_category="other",
                        reviewer_notes="outsider note",
                    ),
                ]
            )
            db.flush()
            for review in db.scalars(select(UserManualReview)).all():
                review.review_updated_at = review.created_at
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

    def test_review_export_stem_prefers_producer_uid_with_web_fallback(self) -> None:
        with TestClient(self.app_factory()):
            pass
        with database.SessionLocal() as db:
            admin = db.scalar(select(User).where(User.email == "admin@example.com"))
            self.assertEqual(_user_review_stem(admin), f"webuser-{admin.id}-data")
            admin.producer_uid = "bio-team-7"
            db.commit()
            db.refresh(admin)
            self.assertEqual(_user_review_stem(admin), "bio-team-7-data")


if __name__ == "__main__":
    unittest.main()
