from unittest.mock import MagicMock, patch
import yaml
from pathlib import Path

from click.testing import CliRunner

from installer.cli import cli


def write_yaml(path: Path, data: dict) -> Path:
    path.write_text(yaml.dump(data))
    return path


def minimal_config(tmp_path: Path) -> Path:
    return write_yaml(tmp_path / "installer.yaml", {
        "preset": "MERN",
        "project_path": str(tmp_path / "app"),
        "domain": "app.com",
    })


def minimal_manifest(tmp_path: Path, config_path: Path) -> Path:
    return write_yaml(tmp_path / "manifest.yaml", {
        "projects": [{
            "name": "myapp",
            "config": str(config_path),
            "servers": [{"host": "1.2.3.4", "user": "ubuntu", "key": "~/.ssh/id_rsa"}],
        }]
    })


# ---------------------------------------------------------------------------
# detect
# ---------------------------------------------------------------------------

def test_detect_local(tmp_path):
    runner = CliRunner()
    with patch("installer.cli._make_runner") as mock_runner, \
         patch("installer.core.detector.detect_environment") as mock_detect:
        mock_detect.return_value = (
            __import__("installer.core.detector", fromlist=["Environment"]).Environment.UBUNTU,
            {"os": "Ubuntu", "version": "22.04"},
        )
        result = runner.invoke(cli, ["detect"])
    assert result.exit_code == 0
    assert "ubuntu" in result.output.lower() or "Ubuntu" in result.output


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

def test_list_projects(tmp_path):
    cfg_path = minimal_config(tmp_path)
    manifest_path = minimal_manifest(tmp_path, cfg_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--manifest", str(manifest_path)])
    assert result.exit_code == 0
    assert "myapp" in result.output


def test_list_no_manifest(tmp_path):
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--manifest", str(tmp_path / "missing.yaml")])
    assert result.exit_code == 1


def test_list_empty_projects(tmp_path):
    manifest_path = write_yaml(tmp_path / "manifest.yaml", {"projects": []})
    runner = CliRunner()
    result = runner.invoke(cli, ["list", "--manifest", str(manifest_path)])
    assert result.exit_code == 0
    assert "No projects" in result.output


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------

def test_verify_runs_checks(tmp_path):
    cfg_path = minimal_config(tmp_path)
    runner = CliRunner()
    with patch("installer.cli._make_runner") as mock_runner_fn, \
         patch("installer.verifier.system_check.SystemCheck.run") as mock_run:
        mock_run.return_value = []
        result = runner.invoke(cli, ["verify", "--config", str(cfg_path)])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# dashboard
# ---------------------------------------------------------------------------

def test_dashboard_shows_port(mocker):
    mocker.patch("uvicorn.run")
    runner = CliRunner()
    result = runner.invoke(cli, ["dashboard", "--port", "9090"])
    assert result.exit_code == 0
    assert "9090" in result.output


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------

def test_install_unknown_project_exits_1(tmp_path):
    cfg_path = minimal_config(tmp_path)
    manifest_path = minimal_manifest(tmp_path, cfg_path)
    runner = CliRunner()
    result = runner.invoke(cli, [
        "install", "--project", "nonexistent", "--manifest", str(manifest_path)
    ])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_install_local_config(tmp_path):
    cfg_path = minimal_config(tmp_path)
    runner = CliRunner()
    with patch("installer.cli._make_runner") as mock_runner_fn, \
         patch("installer.core.engine.Engine.run") as mock_run:
        mock_run.return_value = {
            "project": "app.com",
            "steps": [],
            "stack": {"database": {"engine": "mongodb", "mode": "local"},
                      "backend": {"framework": "node"},
                      "frontend": {"framework": "react"}},
            "issues": [],
        }
        result = runner.invoke(cli, ["install", "--config", str(cfg_path)])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# help always works
# ---------------------------------------------------------------------------

def test_help_shows_all_commands():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for cmd in ["detect", "init", "install", "verify", "status", "deploy", "dashboard", "list"]:
        assert cmd in result.output
