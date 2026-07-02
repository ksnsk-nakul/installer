"""Tests for Installed, Verify, Updates, and Clone sections and their APIs."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from installer.web.server import app

client = TestClient(app)


# ── Installed section ─────────────────────────────────────────────────────────

class TestInstalledSection:
    def test_page_loads(self):
        assert client.get("/installed").status_code == 200

    def test_page_contains_table_structure(self):
        html = client.get("/installed").text
        assert "installed-list" in html

    def test_page_fetches_projects(self):
        html = client.get("/installed").text
        assert "/api/projects" in html

    def test_page_has_verify_button(self):
        html = client.get("/installed").text
        assert "Verify" in html

    def test_page_has_update_button(self):
        html = client.get("/installed").text
        assert "Update" in html

    def test_page_has_clone_button(self):
        html = client.get("/installed").text
        assert "Clone" in html

    def test_page_has_refresh_button(self):
        html = client.get("/installed").text
        assert "Refresh" in html

    def test_status_dot_present(self):
        html = client.get("/installed").text
        assert "status-dot" in html


# ── Verify section + API ──────────────────────────────────────────────────────

class TestVerifySection:
    def test_page_loads(self):
        assert client.get("/verify").status_code == 200

    def test_page_has_select_dropdown(self):
        html = client.get("/verify").text
        assert "verify-select" in html

    def test_page_has_run_button(self):
        html = client.get("/verify").text
        assert "Run Checks" in html

    def test_page_has_results_panel(self):
        html = client.get("/verify").text
        assert "verify-results" in html

    def test_page_fetches_projects(self):
        html = client.get("/verify").text
        assert "/api/projects" in html

    def test_page_posts_to_verify_api(self):
        html = client.get("/verify").text
        assert "/api/verify/" in html

    def test_page_shows_check_badges(self):
        html = client.get("/verify").text
        assert "check-badge" in html

    def test_page_shows_fix_hint_code(self):
        html = client.get("/verify").text
        assert "fix-hint" in html


class TestVerifyAPI:
    def test_unknown_project_returns_404(self, tmp_path, monkeypatch):
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text("projects: []\n")
        monkeypatch.chdir(tmp_path)
        r = client.post("/api/verify/no-such-project")
        assert r.status_code == 404

    def test_no_manifest_returns_404(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        r = client.post("/api/verify/any")
        assert r.status_code == 404

    def test_verify_response_structure(self, tmp_path, monkeypatch):
        cfg = tmp_path / "installer.yaml"
        cfg.write_text(textwrap.dedent("""\
            project_path: /var/www/app
            domain: app.example.com
            stack:
              backend:
                framework: node
        """))
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text(textwrap.dedent(f"""\
            projects:
              - name: myapp
                config: {cfg}
        """))
        monkeypatch.chdir(tmp_path)

        # Mock the system check so it doesn't actually run commands
        import installer.verifier.system_check as sc_mod
        original_run = sc_mod.SystemCheck.run

        def fake_run(self, runner, **kwargs):
            from installer.verifier.system_check import SystemCheckResult
            return [SystemCheckResult(name="test", status="pass", detail="ok")]

        monkeypatch.setattr(sc_mod.SystemCheck, "run", fake_run)

        r = client.post("/api/verify/myapp")
        assert r.status_code == 200
        data = r.json()
        assert "system_checks" in data
        assert "api_checks" in data
        assert "summary" in data
        assert data["project"] == "myapp"

    def test_verify_system_checks_list(self, tmp_path, monkeypatch):
        cfg = tmp_path / "installer.yaml"
        cfg.write_text(textwrap.dedent("""\
            project_path: /var/www/app
            domain: app.example.com
            stack:
              backend:
                framework: laravel
        """))
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text(textwrap.dedent(f"""\
            projects:
              - name: laravel-app
                config: {cfg}
        """))
        monkeypatch.chdir(tmp_path)

        import installer.verifier.system_check as sc_mod
        from installer.verifier.system_check import SystemCheckResult

        monkeypatch.setattr(sc_mod.SystemCheck, "run", lambda self, runner, **kw: [
            SystemCheckResult(name="nginx", status="pass", detail="active"),
            SystemCheckResult(name="php-fpm", status="warn", detail="check config", fix_hint="systemctl restart php8.2-fpm"),
        ])

        r = client.post("/api/verify/laravel-app")
        data = r.json()
        assert len(data["system_checks"]) == 2
        statuses = {c["status"] for c in data["system_checks"]}
        assert "pass" in statuses
        assert "warn" in statuses


# ── Updates section + API ─────────────────────────────────────────────────────

class TestUpdatesSection:
    def test_page_loads(self):
        assert client.get("/updates").status_code == 200

    def test_page_has_refresh_button(self):
        html = client.get("/updates").text
        assert "Refresh" in html

    def test_page_fetches_updates_api(self):
        html = client.get("/updates").text
        assert "/api/updates" in html

    def test_page_has_update_table_structure(self):
        html = client.get("/updates").text
        assert "updates-list" in html


class TestUpdatesAPI:
    def test_no_manifest_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        r = client.get("/api/updates")
        assert r.status_code == 200
        assert r.json() == {"updates": []}

    def test_up_to_date_project_not_in_updates(self, tmp_path, monkeypatch):
        cfg = tmp_path / "installer.yaml"
        cfg.write_text(textwrap.dedent("""\
            project_path: /var/www/app
            domain: app.example.com
            stack:
              backend:
                framework: node
                node_version: "22"
        """))
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text(textwrap.dedent(f"""\
            projects:
              - name: myapp
                config: {cfg}
        """))
        monkeypatch.chdir(tmp_path)
        data = client.get("/api/updates").json()
        # node 22 == latest 22 → no update
        assert all(u["name"] != "myapp" for u in data["updates"])

    def test_outdated_project_appears_in_updates(self, tmp_path, monkeypatch):
        cfg = tmp_path / "installer.yaml"
        cfg.write_text(textwrap.dedent("""\
            project_path: /var/www/app
            domain: app.example.com
            stack:
              backend:
                framework: node
                node_version: "18"
        """))
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text(textwrap.dedent(f"""\
            projects:
              - name: old-app
                config: {cfg}
        """))
        monkeypatch.chdir(tmp_path)
        data = client.get("/api/updates").json()
        names = [u["name"] for u in data["updates"]]
        assert "old-app" in names

    def test_update_response_has_versions(self, tmp_path, monkeypatch):
        cfg = tmp_path / "installer.yaml"
        cfg.write_text(textwrap.dedent("""\
            project_path: /var/www/app
            domain: app.example.com
            stack:
              backend:
                framework: node
                node_version: "18"
        """))
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text(textwrap.dedent(f"""\
            projects:
              - name: old-app
                config: {cfg}
        """))
        monkeypatch.chdir(tmp_path)
        data = client.get("/api/updates").json()
        update = next(u for u in data["updates"] if u["name"] == "old-app")
        assert "current_version" in update
        assert "available_version" in update

    def test_post_update_queues_project(self, tmp_path, monkeypatch):
        manifest = tmp_path / "manifest.yaml"
        cfg = tmp_path / "installer.yaml"
        cfg.write_text("project_path: /v\ndomain: d.com\nstack:\n  backend:\n    framework: node\n")
        manifest.write_text(f"projects:\n  - name: myapp\n    config: {cfg}\n")
        monkeypatch.chdir(tmp_path)
        r = client.post("/api/updates/myapp")
        assert r.status_code == 200
        assert r.json()["status"] == "queued"

    def test_post_update_unknown_project_returns_404(self, tmp_path, monkeypatch):
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text("projects: []\n")
        monkeypatch.chdir(tmp_path)
        r = client.post("/api/updates/ghost")
        assert r.status_code == 404


# ── Clone section + API ───────────────────────────────────────────────────────

class TestCloneSection:
    def test_page_loads(self):
        assert client.get("/clone").status_code == 200

    def test_page_has_source_select(self):
        html = client.get("/clone").text
        assert "clone-source" in html

    def test_page_has_name_input(self):
        html = client.get("/clone").text
        assert "clone-name" in html

    def test_page_has_path_input(self):
        html = client.get("/clone").text
        assert "clone-path" in html

    def test_page_posts_to_clone_api(self):
        html = client.get("/clone").text
        assert "/api/clone" in html

    def test_page_fetches_projects(self):
        html = client.get("/clone").text
        assert "/api/projects" in html


class TestCloneAPI:
    def test_clone_returns_job_id(self, tmp_path, monkeypatch):
        cfg = tmp_path / "installer.yaml"
        cfg.write_text("project_path: /v\ndomain: d.com\nstack:\n  backend:\n    framework: node\n")
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text(f"projects:\n  - name: src\n    config: {cfg}\n")
        monkeypatch.chdir(tmp_path)

        r = client.post("/api/clone", json={
            "source": "src",
            "name": "src-copy",
            "path": str(tmp_path / "src-copy"),
        })
        assert r.status_code == 200
        data = r.json()
        assert "job_id" in data

    def test_clone_missing_source_422(self):
        r = client.post("/api/clone", json={"name": "copy", "path": "/var/www/copy"})
        assert r.status_code == 422

    def test_clone_status_retrievable(self, tmp_path, monkeypatch):
        cfg = tmp_path / "installer.yaml"
        cfg.write_text("project_path: /v\ndomain: d.com\nstack:\n  backend:\n    framework: node\n")
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text(f"projects:\n  - name: src\n    config: {cfg}\n")
        monkeypatch.chdir(tmp_path)

        job_id = client.post("/api/clone", json={
            "source": "src",
            "path": str(tmp_path / "clone-out"),
        }).json()["job_id"]

        r = client.get(f"/api/clone/{job_id}")
        assert r.status_code == 200
        assert "status" in r.json()

    def test_clone_unknown_job_404(self):
        r = client.get("/api/clone/bad-id")
        assert r.status_code == 404
