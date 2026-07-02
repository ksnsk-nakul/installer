"""Tests for /api/projects, /api/presets, /api/health, and project status."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from installer.web.server import app
from installer.core.config import PRESETS

client = TestClient(app)


# ── /api/health ───────────────────────────────────────────────────────────────

class TestHealth:
    def test_returns_ok(self):
        r = client.get("/api/health")
        assert r.status_code == 200

    def test_has_status_and_host(self):
        data = client.get("/api/health").json()
        assert data["status"] == "ok"
        assert isinstance(data["host"], str)
        assert data["host"]  # non-empty


# ── /api/presets ──────────────────────────────────────────────────────────────

class TestPresets:
    def test_returns_200(self):
        assert client.get("/api/presets").status_code == 200

    def test_all_known_presets_present(self):
        data = client.get("/api/presets").json()
        names = {p["name"] for p in data["presets"]}
        for key in PRESETS:
            assert key in names, f"Preset {key!r} missing from /api/presets"

    def test_preset_count_matches_config(self):
        data = client.get("/api/presets").json()
        assert len(data["presets"]) == len(PRESETS)

    def test_each_preset_has_stack(self):
        data = client.get("/api/presets").json()
        for p in data["presets"]:
            assert "stack" in p
            assert isinstance(p["stack"], dict)

    def test_mern_preset_structure(self):
        data = client.get("/api/presets").json()
        mern = next(p for p in data["presets"] if p["name"] == "MERN")
        stack = mern["stack"]
        assert "database" in stack
        assert "backend" in stack

    def test_laravel_presets_exist(self):
        data = client.get("/api/presets").json()
        names = {p["name"] for p in data["presets"]}
        assert "LARAVEL_REACT" in names
        assert "LARAVEL_VUE" in names
        assert "LARAVEL_BLADE" in names

    def test_springboot_preset_exists(self):
        data = client.get("/api/presets").json()
        names = {p["name"] for p in data["presets"]}
        assert "SPRINGBOOT" in names


# ── /api/projects — no manifest ───────────────────────────────────────────────

class TestProjectsNoManifest:
    def test_returns_empty_list_without_manifest(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        r = client.get("/api/projects")
        assert r.status_code == 200
        assert r.json() == {"projects": []}


# ── /api/projects — with manifest ─────────────────────────────────────────────

@pytest.fixture()
def project_dir(tmp_path):
    """Scaffold a minimal project directory with manifest + installer.yaml."""
    cfg = tmp_path / "installer.yaml"
    cfg.write_text(textwrap.dedent("""\
        project_path: /var/www/myapp
        domain: myapp.example.com
        preset: MERN
        stack:
          database:
            engine: mongodb
          backend:
            framework: node
    """))

    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(textwrap.dedent(f"""\
        projects:
          - name: myapp
            config: {cfg}
            servers:
              - host: 1.2.3.4
                user: deploy
    """))
    return tmp_path


class TestProjectsWithManifest:
    def test_lists_project_name(self, project_dir, monkeypatch):
        monkeypatch.chdir(project_dir)
        data = client.get("/api/projects").json()
        assert len(data["projects"]) == 1
        assert data["projects"][0]["name"] == "myapp"

    def test_project_has_config_path(self, project_dir, monkeypatch):
        monkeypatch.chdir(project_dir)
        data = client.get("/api/projects").json()
        p = data["projects"][0]
        assert "config" in p
        assert "installer.yaml" in p["config"]

    def test_project_has_servers(self, project_dir, monkeypatch):
        monkeypatch.chdir(project_dir)
        data = client.get("/api/projects").json()
        servers = data["projects"][0]["servers"]
        assert len(servers) == 1
        assert servers[0]["host"] == "1.2.3.4"
        assert servers[0]["user"] == "deploy"

    def test_multiple_projects(self, tmp_path, monkeypatch):
        for i in range(3):
            cfg = tmp_path / f"app{i}.yaml"
            cfg.write_text(textwrap.dedent(f"""\
                project_path: /var/www/app{i}
                domain: app{i}.example.com
                stack:
                  backend:
                    framework: node
            """))

        manifest = tmp_path / "manifest.yaml"
        manifest.write_text(textwrap.dedent(f"""\
            projects:
              - name: app0
                config: {tmp_path}/app0.yaml
              - name: app1
                config: {tmp_path}/app1.yaml
              - name: app2
                config: {tmp_path}/app2.yaml
        """))
        monkeypatch.chdir(tmp_path)
        data = client.get("/api/projects").json()
        assert len(data["projects"]) == 3
        names = {p["name"] for p in data["projects"]}
        assert names == {"app0", "app1", "app2"}

    def test_project_with_no_servers_has_empty_list(self, tmp_path, monkeypatch):
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
              - name: app
                config: {cfg}
        """))
        monkeypatch.chdir(tmp_path)
        data = client.get("/api/projects").json()
        assert data["projects"][0]["servers"] == []


# ── /api/projects/{name}/status ───────────────────────────────────────────────

class TestProjectStatus:
    def test_returns_unknown_status(self):
        r = client.get("/api/projects/anything/status")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "unknown"
        assert data["name"] == "anything"

    def test_has_checks_list(self):
        data = client.get("/api/projects/myapp/status").json()
        assert isinstance(data["checks"], list)


# ── Explore page renders presets ──────────────────────────────────────────────

class TestExplorePage:
    def test_explore_page_loads(self):
        r = client.get("/explore")
        assert r.status_code == 200

    def test_explore_contains_filter_buttons(self):
        html = client.get("/explore").text
        assert "filter-btn" in html

    def test_explore_api_call_wired_in_template(self):
        html = client.get("/explore").text
        assert "/api/presets" in html

    def test_card_grid_present(self):
        html = client.get("/explore").text
        assert "card-grid" in html

    def test_install_button_wired(self):
        html = client.get("/explore").text
        assert "startInstall" in html
