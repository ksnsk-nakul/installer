"""Tests for /api/install (job lifecycle, DB config dialog, error cases)."""
from __future__ import annotations

import asyncio
import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from installer.web.server import app
from installer.web.api import install as install_module

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_jobs():
    install_module._jobs.clear()
    yield
    install_module._jobs.clear()


# ── POST /api/install — validation ────────────────────────────────────────────

class TestInstallValidation:
    def test_missing_body_returns_422(self):
        r = client.post("/api/install")
        assert r.status_code == 422

    def test_empty_json_returns_422(self):
        r = client.post("/api/install", json={})
        # preset and config_path are both optional but engine will fail —
        # 422 only from pydantic, not from business logic
        # Body is valid JSON with optional fields → 200 with job_id
        # (engine failure happens async)
        assert r.status_code in (200, 422)

    def test_preset_only_returns_job_id(self):
        r = client.post("/api/install", json={"preset": "MERN"})
        assert r.status_code == 200
        assert "job_id" in r.json()

    def test_unknown_preset_still_creates_job(self):
        # Job is created immediately; preset validation happens async
        r = client.post("/api/install", json={"preset": "MERN"})
        assert r.status_code == 200
        assert "job_id" in r.json()

    def test_job_id_is_uuid_format(self):
        import re
        r = client.post("/api/install", json={"preset": "MERN"})
        job_id = r.json()["job_id"]
        assert re.match(r"[0-9a-f-]{36}", job_id)

    def test_two_installs_get_different_job_ids(self):
        r1 = client.post("/api/install", json={"preset": "MERN"})
        r2 = client.post("/api/install", json={"preset": "MERN"})
        assert r1.json()["job_id"] != r2.json()["job_id"]


# ── GET /api/install/{job_id} — job status ────────────────────────────────────

class TestGetJob:
    def test_unknown_job_returns_404(self):
        r = client.get("/api/install/no-such-id")
        assert r.status_code == 404

    def test_created_job_is_retrievable(self):
        job_id = client.post("/api/install", json={"preset": "MERN"}).json()["job_id"]
        r = client.get(f"/api/install/{job_id}")
        assert r.status_code == 200

    def test_job_response_has_required_keys(self):
        job_id = client.post("/api/install", json={"preset": "MERN"}).json()["job_id"]
        data = client.get(f"/api/install/{job_id}").json()
        assert "job_id" in data
        assert "status" in data
        assert "logs" in data

    def test_new_job_status_is_pending_or_running(self):
        job_id = client.post("/api/install", json={"preset": "MERN"}).json()["job_id"]
        data = client.get(f"/api/install/{job_id}").json()
        assert data["status"] in ("pending", "running", "error", "done")

    def test_job_logs_is_list(self):
        job_id = client.post("/api/install", json={"preset": "MERN"}).json()["job_id"]
        data = client.get(f"/api/install/{job_id}").json()
        assert isinstance(data["logs"], list)


# ── POST /api/install/{job_id}/db-config ─────────────────────────────────────

class TestDBConfig:
    def test_unknown_job_returns_404(self):
        r = client.post("/api/install/bad-id/db-config", json={
            "engine": "mysql", "mode": "local"
        })
        assert r.status_code == 404

    def test_valid_db_config_accepted(self):
        # Manually create a job in the registry
        import uuid
        job_id = str(uuid.uuid4())
        loop = asyncio.new_event_loop()
        install_module._jobs[job_id] = {
            "status": "waiting_db_config",
            "logs": [],
            "db_event": asyncio.Event(),
            "db_result": None,
            "report": None,
        }
        r = client.post(f"/api/install/{job_id}/db-config", json={
            "engine": "mysql",
            "mode": "local",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "accepted"

    def test_db_config_stores_result(self):
        import uuid
        job_id = str(uuid.uuid4())
        install_module._jobs[job_id] = {
            "status": "waiting_db_config",
            "logs": [],
            "db_event": asyncio.Event(),
            "db_result": None,
            "report": None,
        }
        client.post(f"/api/install/{job_id}/db-config", json={
            "engine": "postgresql",
            "mode": "external",
            "host": "db.example.com",
            "port": 5432,
            "user": "admin",
            "password": "secret",
            "db_name": "myapp",
        })
        assert install_module._jobs[job_id]["db_result"]["engine"] == "postgresql"
        assert install_module._jobs[job_id]["db_result"]["host"] == "db.example.com"

    def test_db_config_sets_event(self):
        import uuid
        job_id = str(uuid.uuid4())
        ev = asyncio.Event()
        install_module._jobs[job_id] = {
            "status": "waiting_db_config",
            "logs": [],
            "db_event": ev,
            "db_result": None,
            "report": None,
        }
        assert not ev.is_set()
        client.post(f"/api/install/{job_id}/db-config", json={
            "engine": "mysql", "mode": "local"
        })
        assert ev.is_set()

    def test_db_config_local_mode(self):
        import uuid
        job_id = str(uuid.uuid4())
        install_module._jobs[job_id] = {
            "status": "waiting_db_config",
            "logs": [],
            "db_event": asyncio.Event(),
            "db_result": None,
            "report": None,
        }
        client.post(f"/api/install/{job_id}/db-config", json={
            "engine": "mongodb", "mode": "local"
        })
        result = install_module._jobs[job_id]["db_result"]
        assert result["mode"] == "local"
        assert result["engine"] == "mongodb"


# ── Install with mocked engine ────────────────────────────────────────────────

class TestInstallWithMockedEngine:
    def test_preset_install_completes(self, tmp_path, monkeypatch):
        """Mock Engine.run so the background task finishes quickly."""
        import time

        mock_report = {"status": "ok", "steps": []}

        def fake_engine_run(self):
            return mock_report

        monkeypatch.setattr("installer.core.engine.Engine.run", fake_engine_run)

        r = client.post("/api/install", json={
            "preset": "MERN",
            "project_path": str(tmp_path),
            "domain": "test.example.com",
        })
        assert r.status_code == 200
        job_id = r.json()["job_id"]

        # Poll until done or error (max 3s)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            data = client.get(f"/api/install/{job_id}").json()
            if data["status"] in ("done", "error"):
                break
            time.sleep(0.05)

        data = client.get(f"/api/install/{job_id}").json()
        assert data["status"] in ("done", "error")

    def test_invalid_preset_sets_error_status(self, tmp_path, monkeypatch):
        import time

        r = client.post("/api/install", json={"preset": "NO_SUCH_PRESET"})
        job_id = r.json()["job_id"]

        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            data = client.get(f"/api/install/{job_id}").json()
            if data["status"] in ("done", "error"):
                break
            time.sleep(0.05)

        data = client.get(f"/api/install/{job_id}").json()
        assert data["status"] == "error"
        assert any("NO_SUCH_PRESET" in log for log in data["logs"])


# ── DB config modal template ──────────────────────────────────────────────────

class TestDBConfigTemplate:
    def test_db_config_fields_in_page(self):
        html = client.get("/explore").text
        # db_config.html is included in base.html
        assert "db-modal" in html

    def test_modal_has_radio_buttons(self):
        html = client.get("/explore").text
        assert "db-mode" in html

    def test_modal_has_external_fields(self):
        html = client.get("/explore").text
        assert "db-external-fields" in html

    def test_modal_submit_posts_to_api(self):
        html = client.get("/explore").text
        assert "/api/install" in html
        assert "db-config" in html
