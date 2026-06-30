import pytest
import yaml
from pathlib import Path


@pytest.fixture
def tmp_config(tmp_path):
    config = {
        "preset": "MERN",
        "project_path": "/var/www/myapp",
        "domain": "myapp.com",
        "env_file": ".env.production",
        "database": {"engine": "mongodb", "mode": "local"},
        "backend": {"framework": "node"},
        "frontend": {"framework": "react"},
        "verify_api": {
            "url": "http://localhost:3000/api/health",
            "method": "GET",
            "expect_status": 200,
        },
        "monitoring": {"enabled": False},
    }
    config_file = tmp_path / "installer.yaml"
    config_file.write_text(yaml.dump(config))
    return config_file


@pytest.fixture
def tmp_manifest(tmp_path):
    manifest = {
        "projects": [
            {
                "name": "myapp",
                "config": str(tmp_path / "installer.yaml"),
                "servers": [{"host": "192.168.1.10", "user": "ubuntu", "key": "~/.ssh/id_rsa"}],
            }
        ]
    }
    manifest_file = tmp_path / "manifest.yaml"
    manifest_file.write_text(yaml.dump(manifest))
    return manifest_file
