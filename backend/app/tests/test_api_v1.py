from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app import database
from app.config import reset_settings_cache
from app.models import ImportedLiteratureItem


class VersionedApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory(prefix="bio-digest-api-v1-")
        root = Path(self.tmpdir.name)
        self.rules_path = root / "category_rules.yaml"
        self.rules_path.write_text("categories:\n  genomics:\n    keywords: [genome]\n", encoding="utf-8")
        os.environ.update({
            "DATABASE_URL": f"sqlite:///{root / 'api.db'}",
            "INITIAL_ADMIN_EMAIL": "admin@example.com",
            "PRODUCER_SYNC_ENABLED": "false",
            "ACCESS_TRACE_DIR": str(root / "access"),
            "PRODUCER_RULES_PATH": str(self.rules_path),
            "PRODUCER_ROOT": str(root),
            "LITERATURE_API_BOOTSTRAP_TOKEN": "deerflow-test-token",
            "LITERATURE_API_CLIENT_NAME": "deerflow",
        })
        database.engine = None
        database.SessionLocal = None
        reset_settings_cache()
        from app.main import create_app
        self.client = TestClient(create_app())
        self.client.__enter__()
        with database.SessionLocal() as db:
            db.add_all([
                ImportedLiteratureItem(
                    literature_item_key="doi:10.1000/genome",
                    doi="10.1000/genome",
                    title_en="Genome editing in plants",
                    title_zh="植物基因组编辑",
                    abstract="CRISPR genome editing",
                    journal="Nature",
                    publish_date="2026-07-01",
                    category="genomics",
                    authors_json=["Alice Example"],
                    tags_json=["CRISPR"],
                ),
                ImportedLiteratureItem(
                    literature_item_key="doi:10.1000/protein",
                    doi="10.1000/protein",
                    title_en="Protein structure",
                    journal="Science",
                    publish_date="2026-06-01",
                    category="structure",
                ),
            ])
            db.commit()
        self.headers = {"Authorization": "Bearer deerflow-test-token"}

    def tearDown(self) -> None:
        self.client.__exit__(None, None, None)
        for key in (
            "DATABASE_URL", "INITIAL_ADMIN_EMAIL", "PRODUCER_SYNC_ENABLED",
            "ACCESS_TRACE_DIR", "PRODUCER_RULES_PATH", "PRODUCER_ROOT",
            "LITERATURE_API_BOOTSTRAP_TOKEN", "LITERATURE_API_CLIENT_NAME",
        ):
            os.environ.pop(key, None)
        database.engine = None
        database.SessionLocal = None
        reset_settings_cache()
        self.tmpdir.cleanup()

    def test_literature_search_and_batch_require_service_auth(self) -> None:
        self.assertEqual(self.client.get("/api/v1/literature").status_code, 401)
        response = self.client.get("/api/v1/literature?q=genome&page_size=10", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["api_version"], "v1")
        self.assertEqual(payload["total"], 1)
        self.assertEqual(payload["items"][0]["doi"], "10.1000/genome")
        self.assertEqual(payload["items"][0]["authors"], ["Alice Example"])

        batch = self.client.post(
            "/api/v1/literature/batch",
            headers=self.headers,
            json={"keys": ["doi:10.1000/genome", "doi:10.1000/protein"]},
        )
        self.assertEqual(batch.status_code, 200)
        self.assertEqual(len(batch.json()["items"]), 2)

    def test_report_task_is_idempotent_and_accepts_artifact(self) -> None:
        headers = {**self.headers, "Idempotency-Key": "weekly-2026-27"}
        payload = {"report_type": "weekly", "parameters": {"week": "2026-W27"}}
        first = self.client.post("/api/v1/report-tasks", headers=headers, json=payload)
        second = self.client.post("/api/v1/report-tasks", headers=headers, json=payload)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["id"], second.json()["id"])

        conflict = self.client.post(
            "/api/v1/report-tasks",
            headers=headers,
            json={"report_type": "monthly", "parameters": {"month": "2026-07"}},
        )
        self.assertEqual(conflict.status_code, 409)

        task_id = first.json()["id"]
        artifact = self.client.post(
            f"/api/v1/report-tasks/{task_id}/artifacts",
            headers={**self.headers, "Idempotency-Key": "artifact-weekly-2026-27"},
            json={"format": "markdown", "content": "# Weekly report", "metadata": {"papers": 1}},
        )
        self.assertEqual(artifact.status_code, 201)
        task = self.client.get(f"/api/v1/report-tasks/{task_id}", headers=self.headers)
        self.assertEqual(task.json()["status"], "completed")
        self.assertEqual(task.json()["artifacts"][0]["content"], "# Weekly report")

    def test_rule_suggestion_requires_admin_to_publish(self) -> None:
        rules = self.client.get("/api/v1/rules", headers=self.headers)
        self.assertEqual(rules.status_code, 200)
        baseline = rules.json()["content_sha256"]
        self.assertEqual(baseline, hashlib.sha256(self.rules_path.read_bytes()).hexdigest())

        suggestion = self.client.post(
            "/api/v1/rule-suggestions",
            headers={**self.headers, "Idempotency-Key": "rules-1"},
            json={
                "baseline_sha256": baseline,
                "proposed_content": "categories:\n  genomics:\n    keywords: [genome, CRISPR]\n",
                "summary": "Add CRISPR keyword",
            },
        )
        self.assertEqual(suggestion.status_code, 201)
        suggestion_id = suggestion.json()["id"]

        denied = self.client.post(
            f"/api/v1/rule-suggestions/{suggestion_id}/publish",
            headers=self.headers,
        )
        self.assertEqual(denied.status_code, 401)

        login = self.client.post("/api/auth/login", json={"email": "admin@example.com"})
        self.assertEqual(login.status_code, 200)
        published = self.client.post(f"/api/v1/rule-suggestions/{suggestion_id}/publish")
        self.assertEqual(published.status_code, 200)
        self.assertEqual(published.json()["status"], "published")
        self.assertIn("CRISPR", self.rules_path.read_text())

        audit = self.client.get("/api/v1/audit-events", headers=self.headers)
        self.assertEqual(audit.status_code, 200)
        self.assertTrue(any(item["action"] == "rule_suggestion.create" for item in audit.json()["items"]))


if __name__ == "__main__":
    unittest.main()
