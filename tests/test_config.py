import pytest
import yaml
from pathlib import Path

from installer.core.config import (
    load_config,
    load_manifest,
    InstallerConfig,
    ManifestConfig,
    PRESETS,
)


def write_yaml(path: Path, data: dict) -> Path:
    path.write_text(yaml.dump(data))
    return path


# ---------------------------------------------------------------------------
# Preset expansion
# ---------------------------------------------------------------------------

def test_mern_preset_expands(tmp_path):
    cfg_file = write_yaml(tmp_path / "installer.yaml", {
        "preset": "MERN",
        "project_path": "/var/www/app",
        "domain": "app.com",
    })
    cfg = load_config(cfg_file)
    assert cfg.stack.database.engine == "mongodb"
    assert cfg.stack.backend.framework == "node"
    assert cfg.stack.frontend.framework == "react"


def test_preset_layer_override(tmp_path):
    cfg_file = write_yaml(tmp_path / "installer.yaml", {
        "preset": "MERN",
        "project_path": "/var/www/app",
        "domain": "app.com",
        "frontend": {"framework": "vue"},
    })
    cfg = load_config(cfg_file)
    assert cfg.stack.frontend.framework == "vue"
    assert cfg.stack.backend.framework == "node"


def test_all_presets_are_valid(tmp_path):
    for name in PRESETS:
        cfg_file = write_yaml(tmp_path / f"{name}.yaml", {
            "preset": name,
            "project_path": "/var/www/app",
            "domain": "app.com",
        })
        cfg = load_config(cfg_file)
        assert cfg.stack.backend.framework is not None


def test_unknown_preset_raises(tmp_path):
    cfg_file = write_yaml(tmp_path / "installer.yaml", {
        "preset": "BOGUS",
        "project_path": "/var/www/app",
        "domain": "app.com",
    })
    with pytest.raises(ValueError, match="Unknown preset"):
        load_config(cfg_file)


# ---------------------------------------------------------------------------
# Explicit stack (no preset)
# ---------------------------------------------------------------------------

def test_explicit_stack_no_preset(tmp_path):
    cfg_file = write_yaml(tmp_path / "installer.yaml", {
        "project_path": "/var/www/app",
        "domain": "app.com",
        "database": {"engine": "postgresql", "mode": "external", "host": "db.example.com"},
        "backend": {"framework": "laravel", "php_version": "8.2"},
        "frontend": {"framework": "react"},
    })
    cfg = load_config(cfg_file)
    assert cfg.stack.database.engine == "postgresql"
    assert cfg.stack.database.host == "db.example.com"
    assert cfg.stack.backend.php_version == "8.2"


# ---------------------------------------------------------------------------
# Monitoring + verify_api
# ---------------------------------------------------------------------------

def test_verify_api_loaded(tmp_path):
    cfg_file = write_yaml(tmp_path / "installer.yaml", {
        "preset": "MERN",
        "project_path": "/var/www/app",
        "domain": "app.com",
        "verify_api": {"url": "http://localhost:3000/health", "expect_status": 200},
    })
    cfg = load_config(cfg_file)
    assert cfg.verify_api is not None
    assert cfg.verify_api.url == "http://localhost:3000/health"


def test_monitoring_defaults(tmp_path):
    cfg_file = write_yaml(tmp_path / "installer.yaml", {
        "preset": "MERN",
        "project_path": "/var/www/app",
        "domain": "app.com",
    })
    cfg = load_config(cfg_file)
    assert cfg.monitoring.enabled is False


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def test_load_manifest(tmp_path):
    manifest_file = write_yaml(tmp_path / "manifest.yaml", {
        "projects": [
            {
                "name": "myapp",
                "config": "/path/to/installer.yaml",
                "servers": [{"host": "1.2.3.4", "user": "ubuntu", "key": "~/.ssh/id_rsa"}],
            }
        ]
    })
    manifest = load_manifest(manifest_file)
    assert len(manifest.projects) == 1
    assert manifest.projects[0].name == "myapp"
    assert manifest.projects[0].servers[0].host == "1.2.3.4"


def test_empty_manifest(tmp_path):
    manifest_file = write_yaml(tmp_path / "manifest.yaml", {"projects": []})
    manifest = load_manifest(manifest_file)
    assert manifest.projects == []
