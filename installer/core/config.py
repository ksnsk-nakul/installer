from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class DatabaseConfig(BaseModel):
    engine: str = "mysql"           # mysql | postgresql | mongodb | sqlite
    mode: str = "local"             # local | external
    version: Optional[str] = None
    db_name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password_env: Optional[str] = None
    backup_url: Optional[str] = None
    backup_file: Optional[str] = None


class BackendConfig(BaseModel):
    framework: str                  # laravel | node | django | fastapi | flask | java
    php_version: Optional[str] = None
    python_version: Optional[str] = None
    java_version: Optional[str] = None
    node_version: Optional[str] = None
    queue: bool = False
    scheduler: bool = False
    build_tool: Optional[str] = None   # maven | gradle (Java)


class FrontendConfig(BaseModel):
    framework: Optional[str] = None    # react | vue | angular | next | nuxt | blade | jinja2
    build_tool: Optional[str] = None   # vite | webpack | none
    output_dir: str = "dist"


class VerifyAPIConfig(BaseModel):
    url: str
    method: str = "GET"
    expect_status: int = 200
    expect_json: Optional[dict] = None
    timeout: str = "30s"
    retries: int = 3
    headers: Optional[dict] = None


class MonitoringConfig(BaseModel):
    enabled: bool = False
    ping_url: Optional[str] = None
    log_rotation: bool = True
    alert_webhook: Optional[str] = None


class StackConfig(BaseModel):
    database: DatabaseConfig = DatabaseConfig()
    backend: BackendConfig
    frontend: FrontendConfig = FrontendConfig()


# ---------------------------------------------------------------------------
# Root config model
# ---------------------------------------------------------------------------

class InstallerConfig(BaseModel):
    project_path: str
    domain: str
    stack: StackConfig
    env_file: str = ".env"
    preset: Optional[str] = None
    verify_api: Optional[VerifyAPIConfig] = None
    monitoring: MonitoringConfig = MonitoringConfig()

    @field_validator("project_path")
    @classmethod
    def expand_path(cls, v: str) -> str:
        return str(Path(v).expanduser())


# ---------------------------------------------------------------------------
# Manifest models
# ---------------------------------------------------------------------------

class ServerEntry(BaseModel):
    host: str
    user: str = "root"
    key: Optional[str] = None
    password_env: Optional[str] = None
    port: int = 22


class ProjectEntry(BaseModel):
    name: str
    config: str
    servers: list[ServerEntry] = []


class ManifestConfig(BaseModel):
    projects: list[ProjectEntry] = []


# ---------------------------------------------------------------------------
# Named presets
# ---------------------------------------------------------------------------

PRESETS: dict[str, dict] = {
    "MERN": {
        "database": {"engine": "mongodb", "mode": "local"},
        "backend": {"framework": "node"},
        "frontend": {"framework": "react"},
    },
    "MEAN": {
        "database": {"engine": "mongodb", "mode": "local"},
        "backend": {"framework": "node"},
        "frontend": {"framework": "angular"},
    },
    "MEVN": {
        "database": {"engine": "mongodb", "mode": "local"},
        "backend": {"framework": "node"},
        "frontend": {"framework": "vue"},
    },
    "LARAVEL_REACT": {
        "database": {"engine": "mysql", "mode": "local"},
        "backend": {"framework": "laravel"},
        "frontend": {"framework": "react"},
    },
    "LARAVEL_VUE": {
        "database": {"engine": "mysql", "mode": "local"},
        "backend": {"framework": "laravel"},
        "frontend": {"framework": "vue"},
    },
    "LARAVEL_BLADE": {
        "database": {"engine": "mysql", "mode": "local"},
        "backend": {"framework": "laravel"},
        "frontend": {"framework": "blade"},
    },
    "DJANGO_REACT": {
        "database": {"engine": "postgresql", "mode": "local"},
        "backend": {"framework": "django"},
        "frontend": {"framework": "react"},
    },
    "SPRINGBOOT": {
        "database": {"engine": "postgresql", "mode": "local"},
        "backend": {"framework": "java"},
        "frontend": {"framework": None},
    },
}


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base."""
    result = base.copy()
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def load_config(path: str | Path) -> InstallerConfig:
    """Load and validate installer.yaml, expanding preset if set."""
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Invalid installer.yaml at {path}")

    preset_name = data.pop("preset", None)
    if preset_name:
        preset_key = preset_name.upper().replace("+", "_").replace(" ", "_")
        if preset_key not in PRESETS:
            raise ValueError(f"Unknown preset: {preset_name!r}. Valid: {list(PRESETS)}")
        base = PRESETS[preset_key]
        # Merge top-level database/backend/frontend keys from file over preset
        stack_override: dict = {}
        for layer in ("database", "backend", "frontend"):
            if layer in data:
                stack_override[layer] = data.pop(layer)
        merged_stack = _deep_merge(base, stack_override)
        data["stack"] = merged_stack
    else:
        # Expect explicit stack or promote top-level db/backend/frontend keys
        stack: dict = data.pop("stack", {})
        for layer in ("database", "backend", "frontend"):
            if layer in data:
                stack[layer] = data.pop(layer)
        data["stack"] = stack

    return InstallerConfig.model_validate(data)


def load_manifest(path: str | Path) -> ManifestConfig:
    """Load and validate manifest.yaml."""
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Invalid manifest.yaml at {path}")
    return ManifestConfig.model_validate(data)
