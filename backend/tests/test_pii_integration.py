import unittest
import time
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.pii_main import app
from app import intpii_routes


class PiiIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        with intpii_routes._sessions_lock:
            intpii_routes._sessions.clear()

    def tearDown(self):
        self.client.close()

    def test_regex_redaction_and_manual_span(self):
        response = self.client.post(
            "/api/pii/redact/analyze",
            params={"filename": "test.txt", "mode": "regex"},
            content="😀 Alice alice@example.com".encode(),
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["spans"][0]["text"], "alice@example.com")
        response = self.client.post("/api/pii/redact/export", json={
            "doc_id": data["doc_id"], "style": "label",
            "added": [{"unit": 0, "start": 2, "end": 7, "label": "PERSON"}],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "😀 [PERSON] [EMAIL]")
        self.client.delete(f"/api/pii/redact/{data['doc_id']}")
        self.assertEqual(self.client.post("/api/pii/redact/export", json={"doc_id": data["doc_id"]}).status_code, 404)

    def test_regex_evaluation_and_sweep(self):
        payload = {"dataset": "synthetic", "mode": "regex", "n": 2}
        for kind in ("eval", "sweep"):
            created = self.client.post("/api/pii/jobs", json={**payload, "kind": kind})
            self.assertEqual(created.status_code, 202)
            job_id = created.json()["job_id"]
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                status = self.client.get(f"/api/pii/jobs/{job_id}").json()
                if status["status"] in ("completed", "failed"):
                    break
                time.sleep(0.05)
            self.assertEqual(status["status"], "completed", status)
            if kind == "eval":
                self.assertEqual(status["result"]["docs"], 2)
            else:
                self.assertEqual(len(status["result"]["points"]), 7)
        self.assertEqual(self.client.post("/api/pii/jobs", json={**payload, "kind": "eval", "dataset": "../secret.txt"}).status_code, 400)

    def test_expired_sessions_and_capacity(self):
        with intpii_routes._sessions_lock:
            for i in range(intpii_routes.MAX_SESSIONS):
                intpii_routes._sessions[str(i)] = {"t": 100}
        with patch("app.intpii_routes.time.time", return_value=100):
            intpii_routes.purge_expired_sessions()
            self.assertEqual(len(intpii_routes._sessions), intpii_routes.MAX_SESSIONS)
        with patch("app.intpii_routes.time.time", return_value=100 + intpii_routes.SESSION_TTL + 1):
            intpii_routes.purge_expired_sessions()
            self.assertFalse(intpii_routes._sessions)

    def test_cors_exposes_download_filename(self):
        response = self.client.options("/api/pii/redact/export", headers={
            "Origin": "https://frontend-beta-seven-50.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/api/pii/health", headers={"Origin": "https://frontend-beta-seven-50.vercel.app"})
        self.assertEqual(response.headers.get("access-control-expose-headers"), "Content-Disposition")


if __name__ == "__main__":
    unittest.main()
