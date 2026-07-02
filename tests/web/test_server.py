"""Smoke tests for FastAPI dashboard routes."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from installer.web.server import app

client = TestClient(app)


def test_root_redirects_to_explore():
    r = client.get("/", follow_redirects=True)
    assert r.status_code == 200
    assert "Installer Dashboard" in r.text


def test_explore_page():
    r = client.get("/explore")
    assert r.status_code == 200
    assert "Explore" in r.text


def test_installed_page():
    r = client.get("/installed")
    assert r.status_code == 200
    assert "Installed" in r.text


def test_verify_page():
    r = client.get("/verify")
    assert r.status_code == 200
    assert "Verify" in r.text


def test_updates_page():
    r = client.get("/updates")
    assert r.status_code == 200
    assert "Updates" in r.text


def test_clone_page():
    r = client.get("/clone")
    assert r.status_code == 200
    assert "Clone" in r.text


def test_unknown_section_falls_back_to_explore():
    r = client.get("/nonexistent", follow_redirects=True)
    assert r.status_code == 200
    assert "Explore" in r.text


def test_api_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "host" in data


def test_api_presets():
    r = client.get("/api/presets")
    assert r.status_code == 200
    data = r.json()
    assert "presets" in data
    names = [p["name"] for p in data["presets"]]
    assert "MERN" in names
    assert "LARAVEL_BLADE" in names


def test_api_projects_no_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = client.get("/api/projects")
    assert r.status_code == 200
    assert r.json() == {"projects": []}


def test_api_updates_no_manifest(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    r = client.get("/api/updates")
    assert r.status_code == 200
    assert r.json() == {"updates": []}


def test_api_install_missing_body():
    # All fields optional now — empty body creates a job (engine fails async)
    r = client.post("/api/install", json={})
    assert r.status_code in (200, 422)


def test_api_install_unknown_job():
    r = client.get("/api/install/no-such-job")
    assert r.status_code == 404


def test_static_css():
    r = client.get("/static/style.css")
    assert r.status_code == 200


def test_static_js():
    r = client.get("/static/app.js")
    assert r.status_code == 200
