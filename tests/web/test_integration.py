"""End-to-end integration tests: full request flows across multiple APIs."""
from __future__ import annotations

import asyncio
import textwrap
import time
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from installer.web.server import app
from installer.web.ws import broadcaster
from installer.web.api import install as install_module

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_state():
    broadcaster._jobs.clear()
    install_module._jobs.clear()
    yield
    broadcaster._jobs.clear()
    install_module._jobs.clear()


# ── Full navigation flow ──────────────────────────────────────────────────────

class TestNavigationFlow:
    def test_all_sections_load_without_error(self):
        for section in ("explore", "installed", "verify", "updates", "clone"):
            r = client.get(f"/{section}")
            assert r.status_code == 200, f"/{section} failed"

    def test_root_and_explore_return_same_content(self):
        r_root = client.get("/")
        r_explore = client.get("/explore")
        assert r_root.status_code == 200
        assert r_explore.status_code == 200
        # Both render explore.html content
        assert "card-grid" in r_root.text
        assert "card-grid" in r_explore.text

    def test_all_pages_include_sidebar(self):
        for section in ("explore", "installed", "verify", "updates", "clone"):
            html = client.get(f"/{section}").text
            assert "sidebar" in html
            assert "nav-link" in html

    def test_all_pages_include_log_panel(self):
        for section in ("explore", "installed", "verify", "updates", "clone"):
            html = client.get(f"/{section}").text
            assert "log-panel" in html

    def test_all_pages_link_to_ws_via_app_js(self):
        for section in ("explore", "installed", "verify", "updates", "clone"):
            html = client.get(f"/{section}").text
            assert "/static/app.js" in html

    def test_all_pages_include_css(self):
        for section in ("explore", "installed", "verify", "updates", "clone"):
            html = client.get(f"/{section}").text
            assert "/static/style.css" in html

    def test_unknown_section_falls_back_to_explore(self):
        html = client.get("/notarealpage").text
        assert "card-grid" in html


# ── API consistency ───────────────────────────────────────────────────────────

class TestAPIConsistency:
    def test_projects_and_presets_both_have_name_field(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        projects = client.get("/api/projects").json()["projects"]
        presets = client.get("/api/presets").json()["presets"]
        # both empty is fine; if populated, check field
        for p in projects:
            assert "name" in p
        for p in presets:
            assert "name" in p

    def test_health_always_available(self):
        for _ in range(3):
            assert client.get("/api/health").json()["status"] == "ok"

    def test_static_assets_served(self):
        assert client.get("/static/style.css").status_code == 200
        assert client.get("/static/app.js").status_code == 200

    def test_openapi_schema_available(self):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        paths = r.json()["paths"]
        assert "/api/projects" in paths
        assert "/api/presets" in paths
        assert "/api/install" in paths
        assert "/api/health" in paths

    def test_all_api_routes_return_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        json_endpoints = [
            ("GET", "/api/health"),
            ("GET", "/api/presets"),
            ("GET", "/api/projects"),
            ("GET", "/api/updates"),
        ]
        for method, path in json_endpoints:
            r = getattr(client, method.lower())(path)
            assert r.headers["content-type"].startswith("application/json"), \
                f"{method} {path} is not JSON"


# ── Install → WebSocket log flow ──────────────────────────────────────────────

class TestInstallToWSFlow:
    def test_install_job_creates_ws_log_entry(self, monkeypatch):
        """After POST /api/install, the job_id should be streamable via WS."""
        # We don't need the engine to succeed — just verify the job exists
        r = client.post("/api/install", json={"preset": "MERN"})
        assert r.status_code == 200
        job_id = r.json()["job_id"]

        # The install job uses _jobs in install module, not broadcaster
        # Verify the install job is tracked
        assert job_id in install_module._jobs

    def test_ws_broadcaster_job_streams_to_client(self):
        """Independently create a broadcaster job and stream it via WS."""
        job = broadcaster.create("integration-job-1")
        job.append("step: detect")
        job.append("step: install")
        job.finish()

        msgs = []
        try:
            with client.websocket_connect("/ws/logs/integration-job-1") as ws:
                for _ in range(10):
                    try:
                        msg = ws.receive_text()
                        msgs.append(msg)
                        if msg == "[done]":
                            break
                    except WebSocketDisconnect:
                        break
        except WebSocketDisconnect:
            pass

        assert "step: detect" in msgs
        assert "step: install" in msgs
        assert "[done]" in msgs

    def test_ws_ping_not_present_for_instant_jobs(self):
        job = broadcaster.create("integration-job-2")
        job.append("fast line")
        job.finish()

        msgs = []
        try:
            with client.websocket_connect("/ws/logs/integration-job-2") as ws:
                for _ in range(5):
                    try:
                        msg = ws.receive_text()
                        msgs.append(msg)
                        if msg == "[done]":
                            break
                    except WebSocketDisconnect:
                        break
        except WebSocketDisconnect:
            pass

        assert "[ping]" not in msgs
        assert "[done]" in msgs


# ── Manifest-driven flow ──────────────────────────────────────────────────────

class TestManifestDrivenFlow:
    @pytest.fixture()
    def manifest_dir(self, tmp_path):
        for name, framework in [("api-service", "node"), ("cms", "laravel")]:
            cfg = tmp_path / f"{name}.yaml"
            cfg.write_text(textwrap.dedent(f"""\
                project_path: /var/www/{name}
                domain: {name}.example.com
                stack:
                  backend:
                    framework: {framework}
                    node_version: "18"
            """))
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text(textwrap.dedent(f"""\
            projects:
              - name: api-service
                config: {tmp_path}/api-service.yaml
                servers:
                  - host: 10.0.0.1
                    user: ubuntu
              - name: cms
                config: {tmp_path}/cms.yaml
        """))
        return tmp_path

    def test_projects_lists_both(self, manifest_dir, monkeypatch):
        monkeypatch.chdir(manifest_dir)
        data = client.get("/api/projects").json()
        names = {p["name"] for p in data["projects"]}
        assert names == {"api-service", "cms"}

    def test_project_server_info_preserved(self, manifest_dir, monkeypatch):
        monkeypatch.chdir(manifest_dir)
        data = client.get("/api/projects").json()
        svc = next(p for p in data["projects"] if p["name"] == "api-service")
        assert svc["servers"][0]["host"] == "10.0.0.1"
        assert svc["servers"][0]["user"] == "ubuntu"

    def test_updates_finds_outdated_node(self, manifest_dir, monkeypatch):
        monkeypatch.chdir(manifest_dir)
        data = client.get("/api/updates").json()
        # node 18 < latest 22
        names = [u["name"] for u in data["updates"]]
        assert "api-service" in names

    def test_verify_known_project_runs(self, manifest_dir, monkeypatch):
        monkeypatch.chdir(manifest_dir)
        import installer.verifier.system_check as sc_mod
        from installer.verifier.system_check import SystemCheckResult
        monkeypatch.setattr(sc_mod.SystemCheck, "run", lambda self, runner, **kw: [
            SystemCheckResult(name="nginx", status="pass", detail="active"),
        ])
        r = client.post("/api/verify/api-service")
        assert r.status_code == 200
        assert r.json()["project"] == "api-service"

    def test_verify_unknown_project_404(self, manifest_dir, monkeypatch):
        monkeypatch.chdir(manifest_dir)
        r = client.post("/api/verify/ghost")
        assert r.status_code == 404

    def test_clone_known_project(self, manifest_dir, monkeypatch):
        monkeypatch.chdir(manifest_dir)
        r = client.post("/api/clone", json={
            "source": "cms",
            "path": str(manifest_dir / "cms-staging"),
        })
        assert r.status_code == 200
        assert "job_id" in r.json()

    def test_update_known_project_queued(self, manifest_dir, monkeypatch):
        monkeypatch.chdir(manifest_dir)
        r = client.post("/api/updates/cms")
        assert r.status_code == 200
        assert r.json()["status"] == "queued"


# ── DB config round-trip ──────────────────────────────────────────────────────

class TestDBConfigRoundTrip:
    def test_post_local_db_config_accepted(self):
        job_id = str(uuid.uuid4())
        install_module._jobs[job_id] = {
            "status": "waiting_db_config",
            "logs": [],
            "db_event": asyncio.Event(),
            "db_result": None,
            "report": None,
        }
        r = client.post(f"/api/install/{job_id}/db-config", json={
            "engine": "mysql", "mode": "local"
        })
        assert r.status_code == 200
        assert install_module._jobs[job_id]["db_event"].is_set()

    def test_post_external_db_config_accepted(self):
        job_id = str(uuid.uuid4())
        install_module._jobs[job_id] = {
            "status": "waiting_db_config",
            "logs": [],
            "db_event": asyncio.Event(),
            "db_result": None,
            "report": None,
        }
        payload = {
            "engine": "postgresql",
            "mode": "external",
            "host": "pg.prod.internal",
            "port": 5432,
            "user": "app",
            "password": "s3cret",
            "db_name": "appdb",
        }
        r = client.post(f"/api/install/{job_id}/db-config", json=payload)
        assert r.status_code == 200
        stored = install_module._jobs[job_id]["db_result"]
        assert stored["host"] == "pg.prod.internal"
        assert stored["db_name"] == "appdb"

    def test_db_config_then_job_status_still_200(self):
        job_id = str(uuid.uuid4())
        install_module._jobs[job_id] = {
            "status": "waiting_db_config",
            "logs": ["Waiting for DB config"],
            "db_event": asyncio.Event(),
            "db_result": None,
            "report": None,
        }
        client.post(f"/api/install/{job_id}/db-config", json={
            "engine": "mongodb", "mode": "local"
        })
        r = client.get(f"/api/install/{job_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["logs"]  # logs not empty
