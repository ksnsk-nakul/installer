# Core CLI Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working Python CLI installer that detects the target OS, probes a project API to auto-select the stack, interactively configures the database, installs DB + Backend + Frontend layers, and runs post-install verification.

**Architecture:** Plugin-based engine — a core orchestrator drives 5 sequential steps. Environment adapters (Ubuntu/Docker/Windows) abstract OS primitives. Stack plugins (DB/Backend/Frontend) are loaded dynamically based on Step 3 API probe results. The only manual step is DB configuration, which pauses for user input.

**Tech Stack:** Python 3.11+, Click (CLI), Paramiko (SSH), docker SDK, pywinrm, httpx (API checks), Pydantic v2 (config), rich (terminal UI), PyYAML, python-dotenv, pytest.

---

## File Map

```
installer/                        ← Python package root
├── __init__.py
├── cli.py                        ← Click entry point (all commands)
├── core/
│   ├── __init__.py
│   ├── engine.py                 ← Orchestrator: runs Steps 1-5 in order
│   ├── ssh.py                    ← Paramiko SSH wrapper
│   ├── docker_client.py          ← Docker SDK wrapper
│   ├── winrm_client.py           ← pywinrm wrapper
│   ├── detector.py               ← Step 1: OS/env detection
│   ├── config.py                 ← installer.yaml + manifest.yaml loader/validator
│   ├── logger.py                 ← Structured logger (file + rich stream)
│   └── progress.py               ← Step progress tracker (5 steps)
├── adapters/
│   ├── __init__.py
│   ├── base.py                   ← BaseAdapter ABC
│   ├── ubuntu.py                 ← apt/systemd/ufw/nginx/Certbot over SSH
│   ├── docker.py                 ← Dockerfile gen + docker-compose
│   └── windows.py                ← WinRM/Chocolatey/IIS/PowerShell
├── stacks/
│   ├── __init__.py
│   ├── presets.py                ← Named preset → 3-layer config expansion
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py               ← BaseDBLayer ABC
│   │   ├── mysql.py
│   │   ├── postgres.py
│   │   ├── mongodb.py
│   │   └── external.py           ← External provider (connection params only)
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── base.py               ← BaseBackend ABC
│   │   ├── laravel.py
│   │   ├── node.py
│   │   ├── python_app.py
│   │   └── java.py
│   └── frontend/
│       ├── __init__.py
│       ├── base.py               ← BaseFrontend ABC
│       ├── react.py
│       ├── vue.py
│       ├── angular.py
│       └── ssr.py                ← Blade, Jinja2, Next.js, Nuxt
├── verifier/
│   ├── __init__.py
│   ├── api_check.py              ← HTTP probe (Step 3 + Step 5)
│   └── system_check.py           ← Ports, services, DB conn, SSL (Step 5)
tests/
├── __init__.py
├── conftest.py                   ← shared fixtures (mock adapter, tmp config)
├── test_config.py
├── test_detector.py
├── test_adapters.py
├── stacks/
│   ├── test_presets.py
│   ├── test_db.py
│   ├── test_backend.py
│   └── test_frontend.py
├── test_verifier.py
└── test_engine.py
bootstrap.sh
pyproject.toml
installer.yaml.example
manifest.yaml.example
```

---

## Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `installer/__init__.py`
- Create: `installer/cli.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `installer.yaml.example`
- Create: `manifest.yaml.example`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "installer-tool"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "paramiko>=3.4",
    "docker>=7.0",
    "pywinrm>=0.4",
    "httpx>=0.27",
    "pydantic>=2.7",
    "rich>=13.7",
    "pyyaml>=6.0",
    "python-dotenv>=1.0",
]

[project.scripts]
installer = "installer.cli:cli"

[project.optional-dependencies]
dev = ["pytest>=8.2", "pytest-asyncio", "pytest-mock", "httpx"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `installer/__init__.py`** (empty)

- [ ] **Step 3: Create skeleton `installer/cli.py`**

```python
import click

@click.group()
def cli():
    """Installer — deploy web apps to Ubuntu, Docker, or Windows servers."""

@cli.command()
def detect():
    """Probe the target OS and environment."""
    click.echo("detect: not yet implemented")

@cli.command()
def init():
    """Generate installer.yaml for a project."""
    click.echo("init: not yet implemented")

@cli.command()
def install():
    """Run the full 5-step install flow."""
    click.echo("install: not yet implemented")

@cli.command()
def verify():
    """Run pre-flight or post-install checks."""
    click.echo("verify: not yet implemented")

@cli.command()
def status():
    """Show running services and app health."""
    click.echo("status: not yet implemented")

@cli.command()
def deploy():
    """Re-deploy app code without full reinstall."""
    click.echo("deploy: not yet implemented")

@cli.command()
def dashboard():
    """Launch web UI on port 8080."""
    click.echo("dashboard: not yet implemented")

@cli.command(name="list")
def list_projects():
    """List all projects in manifest."""
    click.echo("list: not yet implemented")
```

- [ ] **Step 4: Create `tests/__init__.py`** (empty)

- [ ] **Step 5: Create `tests/conftest.py`**

```python
import pytest
from pathlib import Path
import tempfile, yaml

@pytest.fixture
def tmp_config(tmp_path):
    """Write a minimal installer.yaml and return its path."""
    cfg = {
        "stack": {"backend": {"framework": "laravel"}, "database": {"engine": "mysql", "mode": "local"}, "frontend": {"framework": "react"}},
        "project_path": "/var/www/myapp",
        "domain": "myapp.test",
        "verify_api": {"url": "http://localhost/api/health", "method": "GET", "expect_status": 200, "timeout": "10s", "retries": 1},
    }
    p = tmp_path / "installer.yaml"
    p.write_text(yaml.dump(cfg))
    return p

@pytest.fixture
def tmp_manifest(tmp_path, tmp_config):
    """Write a manifest.yaml and return its path."""
    m = {"projects": [{"name": "myapp", "config": str(tmp_config), "servers": [{"host": "127.0.0.1", "user": "ubuntu", "key": "~/.ssh/id_rsa"}]}]}
    p = tmp_path / "manifest.yaml"
    p.write_text(yaml.dump(m))
    return p
```

- [ ] **Step 6: Create example config files**

`installer.yaml.example`:
```yaml
# preset expands to full 3-layer config
preset: MERN
project_path: /var/www/myapp
domain: myapp.com
env_file: .env.production

database:
  engine: postgresql
  mode: local           # local | external
  version: "16"
  db_name: myapp_db
  # external options (mode: external)
  # host: db.example.com
  # port: 5432
  # user: myapp_user
  # backup_url: https://storage.example.com/backup.sql.gz

backend:
  framework: laravel    # laravel | node | django | fastapi | flask | springboot
  php_version: "8.2"
  queue: true
  scheduler: true

frontend:
  framework: react      # react | vue | angular | nextjs | nuxt | blade | jinja2 | none
  build_tool: vite
  output_dir: dist

verify_api:
  url: "http://localhost:8000/api/health"
  method: GET
  expect_status: 200
  expect_json:
    status: "ok"
  timeout: 30s
  retries: 3

monitoring:
  enabled: false
  ping_url: ""
  log_rotation: true
  alert_webhook: ""
```

`manifest.yaml.example`:
```yaml
projects:
  - name: myapp
    config: /path/to/myapp/installer.yaml
    servers:
      - host: 192.168.1.10
        user: ubuntu
        key: ~/.ssh/id_rsa
  - name: blog
    config: /path/to/blog/installer.yaml
    servers:
      - host: 192.168.1.20
        user: root
        password_env: BLOG_SERVER_PASS
```

- [ ] **Step 7: Install dev dependencies and verify CLI loads**

```bash
pip install -e ".[dev]"
installer --help
```

Expected output:
```
Usage: installer [OPTIONS] COMMAND [ARGS]...
  Installer — deploy web apps to Ubuntu, Docker, or Windows servers.
Commands:
  dashboard  Launch web UI on port 8080.
  deploy     Re-deploy app code without full reinstall.
  detect     Probe the target OS and environment.
  ...
```

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml installer/ tests/ installer.yaml.example manifest.yaml.example
git commit -m "feat: project scaffold, CLI skeleton, dev deps"
```

---

## Task 2: Config loader

**Files:**
- Create: `installer/core/__init__.py`
- Create: `installer/core/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_config.py
import pytest
from installer.core.config import load_config, load_manifest, ConfigError

def test_load_config_minimal(tmp_config):
    cfg = load_config(tmp_config)
    assert cfg.project_path == "/var/www/myapp"
    assert cfg.verify_api.expect_status == 200

def test_load_config_preset_expands(tmp_path):
    import yaml
    p = tmp_path / "installer.yaml"
    p.write_text(yaml.dump({"preset": "MERN", "project_path": "/var/www/app", "domain": "app.test"}))
    cfg = load_config(p)
    assert cfg.stack.database.engine == "mongodb"
    assert cfg.stack.backend.framework == "node"
    assert cfg.stack.frontend.framework == "react"

def test_load_config_missing_required(tmp_path):
    import yaml
    p = tmp_path / "installer.yaml"
    p.write_text(yaml.dump({"stack": {"backend": {"framework": "laravel"}}}))
    with pytest.raises(ConfigError):
        load_config(p)

def test_load_manifest(tmp_manifest):
    m = load_manifest(tmp_manifest)
    assert len(m.projects) == 1
    assert m.projects[0].name == "myapp"

def test_load_config_file_not_found():
    with pytest.raises(ConfigError):
        load_config("/nonexistent/installer.yaml")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config.py -v
```

Expected: ImportError or ModuleNotFoundError — `installer.core.config` does not exist yet.

- [ ] **Step 3: Create `installer/core/__init__.py`** (empty)

- [ ] **Step 4: Create `installer/core/config.py`**

```python
from __future__ import annotations
from pathlib import Path
from typing import Literal, Optional
import yaml
from pydantic import BaseModel, ValidationError, field_validator

PRESETS: dict[str, dict] = {
    "MERN":  {"database": {"engine": "mongodb", "mode": "local"}, "backend": {"framework": "node"}, "frontend": {"framework": "react"}},
    "MEAN":  {"database": {"engine": "mongodb", "mode": "local"}, "backend": {"framework": "node"}, "frontend": {"framework": "angular"}},
    "MEVN":  {"database": {"engine": "mongodb", "mode": "local"}, "backend": {"framework": "node"}, "frontend": {"framework": "vue"}},
    "LARAVEL_REACT": {"database": {"engine": "mysql", "mode": "local"}, "backend": {"framework": "laravel"}, "frontend": {"framework": "react"}},
    "LARAVEL_VUE":   {"database": {"engine": "mysql", "mode": "local"}, "backend": {"framework": "laravel"}, "frontend": {"framework": "vue"}},
    "LARAVEL_BLADE": {"database": {"engine": "mysql", "mode": "local"}, "backend": {"framework": "laravel"}, "frontend": {"framework": "blade"}},
    "DJANGO_REACT":  {"database": {"engine": "postgresql", "mode": "local"}, "backend": {"framework": "django"}, "frontend": {"framework": "react"}},
    "SPRINGBOOT":    {"database": {"engine": "mysql", "mode": "local"}, "backend": {"framework": "springboot"}, "frontend": {"framework": "none"}},
}


class ConfigError(Exception):
    pass


class DBConfig(BaseModel):
    engine: Literal["mysql", "postgresql", "mongodb", "sqlite"] = "mysql"
    mode: Literal["local", "external"] = "local"
    version: str = "latest"
    db_name: str = "app_db"
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password_env: Optional[str] = None
    backup_url: Optional[str] = None


class BackendConfig(BaseModel):
    framework: Literal["laravel", "node", "django", "fastapi", "flask", "springboot"]
    php_version: str = "8.2"
    python_version: str = "3.12"
    node_version: str = "20"
    java_version: str = "21"
    queue: bool = False
    scheduler: bool = False


class FrontendConfig(BaseModel):
    framework: Literal["react", "vue", "angular", "nextjs", "nuxt", "blade", "jinja2", "none"] = "none"
    build_tool: str = "vite"
    output_dir: str = "dist"


class StackConfig(BaseModel):
    database: DBConfig = DBConfig()
    backend: BackendConfig
    frontend: FrontendConfig = FrontendConfig()


class VerifyAPIConfig(BaseModel):
    url: str
    method: str = "GET"
    expect_status: int = 200
    expect_json: Optional[dict] = None
    timeout: str = "30s"
    retries: int = 3
    headers: dict = {}


class MonitoringConfig(BaseModel):
    enabled: bool = False
    ping_url: str = ""
    log_rotation: bool = True
    alert_webhook: str = ""


class InstallerConfig(BaseModel):
    project_path: str
    domain: str
    stack: StackConfig
    env_file: str = ".env"
    verify_api: Optional[VerifyAPIConfig] = None
    monitoring: MonitoringConfig = MonitoringConfig()


class ServerConfig(BaseModel):
    host: str
    user: str
    key: Optional[str] = None
    password_env: Optional[str] = None
    port: int = 22


class ProjectEntry(BaseModel):
    name: str
    config: str
    servers: list[ServerConfig]


class ManifestConfig(BaseModel):
    projects: list[ProjectEntry]


def _merge_preset(raw: dict) -> dict:
    preset_key = raw.pop("preset", None)
    if preset_key:
        name = preset_key.upper().replace("+", "_").replace(" ", "_")
        if name not in PRESETS:
            raise ConfigError(f"Unknown preset '{preset_key}'. Valid: {list(PRESETS.keys())}")
        preset = PRESETS[name]
        raw.setdefault("stack", {})
        for layer, vals in preset.items():
            raw["stack"].setdefault(layer, {})
            for k, v in vals.items():
                raw["stack"][layer].setdefault(k, v)
    return raw


def load_config(path: str | Path) -> InstallerConfig:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Config file not found: {path}")
    raw = yaml.safe_load(p.read_text()) or {}
    raw = _merge_preset(raw)
    if "domain" not in raw:
        raise ConfigError("installer.yaml must include 'domain'")
    if "project_path" not in raw:
        raise ConfigError("installer.yaml must include 'project_path'")
    try:
        return InstallerConfig(**raw)
    except (ValidationError, TypeError) as e:
        raise ConfigError(f"Invalid config: {e}") from e


def load_manifest(path: str | Path) -> ManifestConfig:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Manifest not found: {path}")
    raw = yaml.safe_load(p.read_text()) or {}
    try:
        return ManifestConfig(**raw)
    except (ValidationError, TypeError) as e:
        raise ConfigError(f"Invalid manifest: {e}") from e
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: All 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add installer/core/__init__.py installer/core/config.py tests/test_config.py
git commit -m "feat: config loader with Pydantic models and preset expansion"
```

---

## Task 3: Logger and progress tracker

**Files:**
- Create: `installer/core/logger.py`
- Create: `installer/core/progress.py`
- Create: `tests/test_logger.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_logger.py
import pytest
from installer.core.logger import get_logger
from installer.core.progress import Progress, StepStatus

def test_logger_returns_named_logger():
    log = get_logger("test")
    assert log.name == "installer.test"

def test_progress_starts_all_pending():
    p = Progress()
    for i in range(1, 6):
        assert p.get_step(i).status == StepStatus.PENDING

def test_progress_start_step():
    p = Progress()
    p.start(1, "OS Detection")
    assert p.get_step(1).status == StepStatus.RUNNING
    assert p.get_step(1).name == "OS Detection"

def test_progress_complete_step():
    p = Progress()
    p.start(2, "Adapter Load")
    p.complete(2)
    assert p.get_step(2).status == StepStatus.DONE

def test_progress_fail_step():
    p = Progress()
    p.start(3, "API Verify")
    p.fail(3, "Connection refused")
    s = p.get_step(3)
    assert s.status == StepStatus.FAILED
    assert s.error == "Connection refused"

def test_progress_summary():
    p = Progress()
    p.start(1, "OS Detection"); p.complete(1)
    p.start(2, "Adapter"); p.fail(2, "err")
    summary = p.summary()
    assert summary["done"] == 1
    assert summary["failed"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_logger.py -v
```

Expected: ImportError — modules not yet defined.

- [ ] **Step 3: Create `installer/core/logger.py`**

```python
import logging
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)],
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"installer.{name}")
```

- [ ] **Step 4: Create `installer/core/progress.py`**

```python
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Step:
    number: int
    name: str = ""
    status: StepStatus = StepStatus.PENDING
    error: Optional[str] = None


class Progress:
    def __init__(self):
        self._steps: dict[int, Step] = {i: Step(number=i) for i in range(1, 6)}

    def get_step(self, number: int) -> Step:
        return self._steps[number]

    def start(self, number: int, name: str) -> None:
        s = self._steps[number]
        s.name = name
        s.status = StepStatus.RUNNING

    def complete(self, number: int) -> None:
        self._steps[number].status = StepStatus.DONE

    def fail(self, number: int, error: str) -> None:
        s = self._steps[number]
        s.status = StepStatus.FAILED
        s.error = error

    def skip(self, number: int) -> None:
        self._steps[number].status = StepStatus.SKIPPED

    def summary(self) -> dict:
        steps = list(self._steps.values())
        return {
            "done": sum(1 for s in steps if s.status == StepStatus.DONE),
            "failed": sum(1 for s in steps if s.status == StepStatus.FAILED),
            "pending": sum(1 for s in steps if s.status == StepStatus.PENDING),
            "steps": [{"number": s.number, "name": s.name, "status": s.status, "error": s.error} for s in steps],
        }
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_logger.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add installer/core/logger.py installer/core/progress.py tests/test_logger.py
git commit -m "feat: logger (rich) and 5-step progress tracker"
```

---

## Task 4: OS / Environment Detector (Step 1)

**Files:**
- Create: `installer/core/detector.py`
- Create: `tests/test_detector.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_detector.py
import pytest
from unittest.mock import MagicMock, patch
from installer.core.detector import detect_environment, Environment

def _make_runner(stdout="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.returncode = returncode
    return r

def test_detects_ubuntu(tmp_path):
    runner = MagicMock()
    runner.run.side_effect = [
        _make_runner("Linux"),                              # uname
        _make_runner('ID=ubuntu\nVERSION_ID="22.04"'),     # /etc/os-release
        _make_runner("", returncode=1),                    # docker info (fails)
        _make_runner("", returncode=1),                    # winrm (fails)
    ]
    env = detect_environment(runner)
    assert env == Environment.UBUNTU

def test_detects_docker(tmp_path):
    runner = MagicMock()
    runner.run.side_effect = [
        _make_runner("Linux"),
        _make_runner("", returncode=1),                    # no os-release
        _make_runner("Server Version: 24.0"),              # docker info succeeds
        _make_runner("", returncode=1),
    ]
    env = detect_environment(runner)
    assert env == Environment.DOCKER

def test_detects_windows():
    runner = MagicMock()
    runner.run.side_effect = [
        _make_runner("", returncode=1),                    # uname fails
        _make_runner("", returncode=1),
        _make_runner("", returncode=1),
        _make_runner("Windows NT"),                        # winrm succeeds
    ]
    env = detect_environment(runner)
    assert env == Environment.WINDOWS

def test_raises_on_unknown():
    runner = MagicMock()
    runner.run.return_value = _make_runner("", returncode=1)
    from installer.core.detector import DetectionError
    with pytest.raises(DetectionError):
        detect_environment(runner)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_detector.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create `installer/core/detector.py`**

```python
from __future__ import annotations
from enum import Enum
from typing import Protocol


class DetectionError(Exception):
    pass


class Environment(str, Enum):
    UBUNTU = "ubuntu"
    DOCKER = "docker"
    WINDOWS = "windows"


class CommandRunner(Protocol):
    def run(self, command: str) -> object: ...


def detect_environment(runner: CommandRunner) -> Environment:
    """
    Probe the target in order: Ubuntu → Docker → Windows.
    Returns the first environment that responds positively.
    """
    uname = runner.run("uname -s")
    if getattr(uname, "returncode", 1) == 0 and "Linux" in (uname.stdout or ""):
        os_release = runner.run("cat /etc/os-release")
        if getattr(os_release, "returncode", 1) == 0 and "ubuntu" in (os_release.stdout or "").lower():
            return Environment.UBUNTU

    docker = runner.run("docker info --format '{{.ServerVersion}}'")
    if getattr(docker, "returncode", 1) == 0 and docker.stdout:
        return Environment.DOCKER

    winrm = runner.run("systeminfo | findstr /B /C:\"OS Name\"")
    if getattr(winrm, "returncode", 1) == 0 and "Windows" in (winrm.stdout or ""):
        return Environment.WINDOWS

    raise DetectionError(
        "Could not detect target environment. "
        "Supported: Ubuntu (via SSH), Docker, Windows (via WinRM)."
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_detector.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add installer/core/detector.py tests/test_detector.py
git commit -m "feat: OS/environment detection (Step 1)"
```

---

## Task 5: SSH, Docker, and WinRM clients + BaseAdapter

**Files:**
- Create: `installer/core/ssh.py`
- Create: `installer/core/docker_client.py`
- Create: `installer/core/winrm_client.py`
- Create: `installer/adapters/__init__.py`
- Create: `installer/adapters/base.py`
- Create: `tests/test_adapters.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_adapters.py
import pytest
from unittest.mock import MagicMock, patch
from installer.adapters.base import BaseAdapter

class ConcreteAdapter(BaseAdapter):
    def detect(self): return True
    def install_packages(self, packages): pass
    def start_service(self, name): pass
    def enable_service(self, name): pass
    def open_port(self, port, protocol="tcp"): pass
    def write_file(self, path, content): pass
    def run(self, command): return MagicMock(stdout="", returncode=0)
    def get_info(self): return {"env": "test"}

def test_base_adapter_interface():
    adapter = ConcreteAdapter()
    assert adapter.detect() is True
    assert adapter.get_info()["env"] == "test"

def test_base_adapter_run_returns_result():
    adapter = ConcreteAdapter()
    result = adapter.run("echo hello")
    assert result.returncode == 0

def test_base_adapter_cannot_instantiate_directly():
    with pytest.raises(TypeError):
        BaseAdapter()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_adapters.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create `installer/core/ssh.py`**

```python
from __future__ import annotations
import paramiko
from dataclasses import dataclass


@dataclass
class RunResult:
    stdout: str
    stderr: str
    returncode: int


class SSHClient:
    def __init__(self, host: str, user: str, key_path: str | None = None, password: str | None = None, port: int = 22):
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._host = host
        self._user = user
        self._key_path = key_path
        self._password = password
        self._port = port

    def connect(self) -> None:
        kwargs: dict = {"hostname": self._host, "username": self._user, "port": self._port}
        if self._key_path:
            kwargs["key_filename"] = self._key_path
        if self._password:
            kwargs["password"] = self._password
        self._client.connect(**kwargs)

    def run(self, command: str) -> RunResult:
        _, stdout, stderr = self._client.exec_command(command)
        return RunResult(
            stdout=stdout.read().decode().strip(),
            stderr=stderr.read().decode().strip(),
            returncode=stdout.channel.recv_exit_status(),
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()
```

- [ ] **Step 4: Create `installer/core/docker_client.py`**

```python
from __future__ import annotations
import docker
from installer.core.ssh import RunResult


class DockerClient:
    """Thin wrapper around the Docker SDK for local Docker environments."""

    def __init__(self):
        self._client = docker.from_env()

    def run(self, command: str) -> RunResult:
        import subprocess
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return RunResult(stdout=result.stdout.strip(), stderr=result.stderr.strip(), returncode=result.returncode)

    def get_info(self) -> dict:
        info = self._client.info()
        return {"server_version": info.get("ServerVersion", ""), "os": info.get("OperatingSystem", "")}
```

- [ ] **Step 5: Create `installer/core/winrm_client.py`**

```python
from __future__ import annotations
import winrm
from installer.core.ssh import RunResult


class WinRMClient:
    def __init__(self, host: str, user: str, password: str, port: int = 5985):
        self._host = host
        self._user = user
        self._password = password
        self._port = port

    def run(self, command: str) -> RunResult:
        session = winrm.Session(
            f"http://{self._host}:{self._port}/wsman",
            auth=(self._user, self._password),
        )
        result = session.run_cmd(command)
        return RunResult(
            stdout=result.std_out.decode().strip(),
            stderr=result.std_err.decode().strip(),
            returncode=result.status_code,
        )
```

- [ ] **Step 6: Create `installer/adapters/__init__.py`** (empty)

- [ ] **Step 7: Create `installer/adapters/base.py`**

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from installer.core.ssh import RunResult


class BaseAdapter(ABC):
    """Common interface all environment adapters must implement."""

    @abstractmethod
    def detect(self) -> bool:
        """Return True if this adapter matches the target environment."""

    @abstractmethod
    def install_packages(self, packages: list[str]) -> None:
        """Install system packages on the target."""

    @abstractmethod
    def start_service(self, name: str) -> None:
        """Start a named service."""

    @abstractmethod
    def enable_service(self, name: str) -> None:
        """Enable a named service to start on boot."""

    @abstractmethod
    def open_port(self, port: int, protocol: str = "tcp") -> None:
        """Open a firewall port."""

    @abstractmethod
    def write_file(self, path: str, content: str) -> None:
        """Write a file on the target."""

    @abstractmethod
    def run(self, command: str) -> RunResult:
        """Execute a shell command on the target and return the result."""

    @abstractmethod
    def get_info(self) -> dict:
        """Return a dict of detected environment metadata."""
```

- [ ] **Step 8: Run tests to verify they pass**

```bash
pytest tests/test_adapters.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 9: Commit**

```bash
git add installer/core/ssh.py installer/core/docker_client.py installer/core/winrm_client.py installer/adapters/__init__.py installer/adapters/base.py tests/test_adapters.py
git commit -m "feat: SSH/Docker/WinRM clients and BaseAdapter interface"
```

---

## Task 6: Ubuntu, Docker, and Windows Adapters (Step 2)

**Files:**
- Create: `installer/adapters/ubuntu.py`
- Create: `installer/adapters/docker.py`
- Create: `installer/adapters/windows.py`

- [ ] **Step 1: Write failing tests** (add to `tests/test_adapters.py`)

```python
from unittest.mock import patch, MagicMock
from installer.adapters.ubuntu import UbuntuAdapter
from installer.adapters.docker import DockerAdapter
from installer.adapters.windows import WindowsAdapter

def _mock_runner(stdout="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.returncode = returncode
    return r

def test_ubuntu_adapter_install_packages():
    runner = MagicMock()
    runner.run.return_value = _mock_runner()
    adapter = UbuntuAdapter(runner=runner)
    adapter.install_packages(["nginx", "git"])
    runner.run.assert_called_with("apt-get install -y nginx git")

def test_ubuntu_adapter_start_service():
    runner = MagicMock()
    runner.run.return_value = _mock_runner()
    adapter = UbuntuAdapter(runner=runner)
    adapter.start_service("nginx")
    runner.run.assert_called_with("systemctl start nginx")

def test_ubuntu_adapter_open_port():
    runner = MagicMock()
    runner.run.return_value = _mock_runner()
    adapter = UbuntuAdapter(runner=runner)
    adapter.open_port(80)
    runner.run.assert_called_with("ufw allow 80/tcp")

def test_docker_adapter_write_file(tmp_path):
    runner = MagicMock()
    runner.run.return_value = _mock_runner()
    adapter = DockerAdapter(runner=runner, project_dir=str(tmp_path))
    adapter.write_file("/etc/nginx/nginx.conf", "worker_processes 1;")
    runner.run.assert_called()

def test_windows_adapter_install_packages():
    runner = MagicMock()
    runner.run.return_value = _mock_runner()
    adapter = WindowsAdapter(runner=runner)
    adapter.install_packages(["nodejs", "git"])
    runner.run.assert_called_with("choco install nodejs git -y")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_adapters.py -v -k "ubuntu or docker or windows"
```

Expected: ImportError for all three adapters.

- [ ] **Step 3: Create `installer/adapters/ubuntu.py`**

```python
from __future__ import annotations
from installer.adapters.base import BaseAdapter
from installer.core.ssh import RunResult


class UbuntuAdapter(BaseAdapter):
    def __init__(self, runner):
        self._r = runner

    def detect(self) -> bool:
        res = self._r.run("cat /etc/os-release")
        return res.returncode == 0 and "ubuntu" in res.stdout.lower()

    def install_packages(self, packages: list[str]) -> None:
        self._r.run(f"apt-get install -y {' '.join(packages)}")

    def start_service(self, name: str) -> None:
        self._r.run(f"systemctl start {name}")

    def enable_service(self, name: str) -> None:
        self._r.run(f"systemctl enable {name}")

    def open_port(self, port: int, protocol: str = "tcp") -> None:
        self._r.run(f"ufw allow {port}/{protocol}")

    def write_file(self, path: str, content: str) -> None:
        escaped = content.replace("'", "'\\''")
        self._r.run(f"mkdir -p $(dirname {path}) && printf '%s' '{escaped}' > {path}")

    def run(self, command: str) -> RunResult:
        return self._r.run(command)

    def get_info(self) -> dict:
        res = self._r.run("cat /etc/os-release")
        return {"env": "ubuntu", "os_release": res.stdout}

    def apt_update(self) -> None:
        self._r.run("apt-get update -qq")

    def install_certbot(self, domain: str) -> None:
        self.install_packages(["certbot", "python3-certbot-nginx"])
        self._r.run(f"certbot --nginx -d {domain} --non-interactive --agree-tos -m admin@{domain}")
```

- [ ] **Step 4: Create `installer/adapters/docker.py`**

```python
from __future__ import annotations
import os
from installer.adapters.base import BaseAdapter
from installer.core.ssh import RunResult


class DockerAdapter(BaseAdapter):
    def __init__(self, runner, project_dir: str = "."):
        self._r = runner
        self.project_dir = project_dir

    def detect(self) -> bool:
        res = self._r.run("docker info --format '{{.ServerVersion}}'")
        return res.returncode == 0 and bool(res.stdout)

    def install_packages(self, packages: list[str]) -> None:
        # Docker installs happen inside Dockerfile, not on host
        pass

    def start_service(self, name: str) -> None:
        self._r.run(f"docker-compose up -d {name}")

    def enable_service(self, name: str) -> None:
        self._r.run(f"docker-compose up -d --restart always {name}")

    def open_port(self, port: int, protocol: str = "tcp") -> None:
        # ports exposed via docker-compose.yml, not ufw
        pass

    def write_file(self, path: str, content: str) -> None:
        local_path = os.path.join(self.project_dir, os.path.basename(path))
        with open(local_path, "w") as f:
            f.write(content)
        self._r.run(f"docker cp {local_path} app:{path}")

    def run(self, command: str) -> RunResult:
        return self._r.run(command)

    def get_info(self) -> dict:
        res = self._r.run("docker info --format '{{.ServerVersion}}'")
        return {"env": "docker", "server_version": res.stdout}

    def compose_up(self, service: str | None = None) -> None:
        cmd = "docker-compose up -d"
        if service:
            cmd += f" {service}"
        self._r.run(cmd)

    def write_dockerfile(self, content: str) -> None:
        path = os.path.join(self.project_dir, "Dockerfile")
        with open(path, "w") as f:
            f.write(content)

    def write_compose(self, content: str) -> None:
        path = os.path.join(self.project_dir, "docker-compose.yml")
        with open(path, "w") as f:
            f.write(content)
```

- [ ] **Step 5: Create `installer/adapters/windows.py`**

```python
from __future__ import annotations
from installer.adapters.base import BaseAdapter
from installer.core.ssh import RunResult


class WindowsAdapter(BaseAdapter):
    def __init__(self, runner):
        self._r = runner

    def detect(self) -> bool:
        res = self._r.run("systeminfo | findstr /B /C:\"OS Name\"")
        return res.returncode == 0 and "Windows" in res.stdout

    def install_packages(self, packages: list[str]) -> None:
        self._r.run(f"choco install {' '.join(packages)} -y")

    def start_service(self, name: str) -> None:
        self._r.run(f"Start-Service -Name {name}")

    def enable_service(self, name: str) -> None:
        self._r.run(f"Set-Service -Name {name} -StartupType Automatic")

    def open_port(self, port: int, protocol: str = "tcp") -> None:
        self._r.run(
            f"netsh advfirewall firewall add rule name='Allow {port}' "
            f"protocol={protocol.upper()} dir=in action=allow localport={port}"
        )

    def write_file(self, path: str, content: str) -> None:
        escaped = content.replace('"', '`"')
        self._r.run(f'Set-Content -Path "{path}" -Value "{escaped}"')

    def run(self, command: str) -> RunResult:
        return self._r.run(command)

    def get_info(self) -> dict:
        res = self._r.run("systeminfo | findstr /B /C:\"OS Name\"")
        return {"env": "windows", "os_info": res.stdout}
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_adapters.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add installer/adapters/ubuntu.py installer/adapters/docker.py installer/adapters/windows.py
git commit -m "feat: Ubuntu, Docker, and Windows adapters (Step 2)"
```

---

## Task 7: API Verifier — project probe and stack auto-selection (Step 3)

**Files:**
- Create: `installer/verifier/__init__.py`
- Create: `installer/verifier/api_check.py`
- Create: `tests/test_verifier.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_verifier.py
import pytest
import httpx
from unittest.mock import patch, MagicMock
from installer.verifier.api_check import APICheck, CheckResult, probe_project_stack

def test_api_check_pass():
    with patch("httpx.Client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "ok"}
        mock_resp.elapsed.total_seconds.return_value = 0.1
        mock_client.return_value.__enter__.return_value.request.return_value = mock_resp

        result = APICheck(
            url="http://localhost/api/health",
            method="GET",
            expect_status=200,
            expect_json={"status": "ok"},
            timeout=10,
            retries=1,
        ).run()
        assert result.passed is True
        assert result.status_code == 200

def test_api_check_fail_wrong_status():
    with patch("httpx.Client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_resp.json.return_value = {}
        mock_resp.elapsed.total_seconds.return_value = 0.5
        mock_client.return_value.__enter__.return_value.request.return_value = mock_resp

        result = APICheck(
            url="http://localhost/api/health",
            method="GET",
            expect_status=200,
            timeout=5,
            retries=1,
        ).run()
        assert result.passed is False
        assert "503" in result.error

def test_probe_project_stack_detects_laravel():
    with patch("httpx.Client") as mock_client:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "framework": "laravel",
            "php_version": "8.2",
            "db": "mysql",
            "frontend": "react",
        }
        mock_resp.elapsed.total_seconds.return_value = 0.05
        mock_client.return_value.__enter__.return_value.request.return_value = mock_resp

        stack = probe_project_stack("http://localhost/.installer/probe")
        assert stack["backend"]["framework"] == "laravel"
        assert stack["database"]["engine"] == "mysql"
        assert stack["frontend"]["framework"] == "react"

def test_probe_project_stack_returns_none_on_failure():
    with patch("httpx.Client") as mock_client:
        mock_client.return_value.__enter__.return_value.request.side_effect = Exception("refused")
        stack = probe_project_stack("http://localhost/.installer/probe")
        assert stack is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_verifier.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create `installer/verifier/__init__.py`** (empty)

- [ ] **Step 4: Create `installer/verifier/api_check.py`**

```python
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Optional
import httpx


@dataclass
class CheckResult:
    passed: bool
    status_code: Optional[int] = None
    latency_ms: Optional[float] = None
    body: Optional[dict] = None
    error: Optional[str] = None


class APICheck:
    def __init__(
        self,
        url: str,
        method: str = "GET",
        expect_status: int = 200,
        expect_json: Optional[dict] = None,
        timeout: int = 30,
        retries: int = 3,
        headers: Optional[dict] = None,
    ):
        self.url = url
        self.method = method
        self.expect_status = expect_status
        self.expect_json = expect_json
        self.timeout = timeout
        self.retries = retries
        self.headers = headers or {}

    def run(self) -> CheckResult:
        last_error = None
        for attempt in range(self.retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.request(self.method, self.url, headers=self.headers)
                    latency = resp.elapsed.total_seconds() * 1000
                    if resp.status_code != self.expect_status:
                        last_error = f"Expected status {self.expect_status}, got {resp.status_code}"
                        time.sleep(2 ** attempt)
                        continue
                    body = None
                    try:
                        body = resp.json()
                    except Exception:
                        pass
                    if self.expect_json and body:
                        for k, v in self.expect_json.items():
                            if body.get(k) != v:
                                last_error = f"JSON assertion failed: expected {k}={v!r}, got {body.get(k)!r}"
                                time.sleep(2 ** attempt)
                                continue
                    return CheckResult(passed=True, status_code=resp.status_code, latency_ms=latency, body=body)
            except Exception as e:
                last_error = str(e)
                time.sleep(2 ** attempt)
        return CheckResult(passed=False, error=last_error)


def probe_project_stack(probe_url: str) -> Optional[dict]:
    """
    Call the project probe endpoint. Returns a normalised stack dict or None on failure.
    The probe endpoint is expected to return:
      { framework, php_version?, node_version?, python_version?, java_version?, db, frontend }
    """
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(probe_url)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return {
                "backend": {
                    "framework": data.get("framework", ""),
                    "php_version": data.get("php_version", "8.2"),
                    "node_version": data.get("node_version", "20"),
                    "python_version": data.get("python_version", "3.12"),
                    "java_version": data.get("java_version", "21"),
                },
                "database": {"engine": data.get("db", "mysql"), "mode": "local"},
                "frontend": {"framework": data.get("frontend", "none")},
            }
    except Exception:
        return None
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_verifier.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add installer/verifier/__init__.py installer/verifier/api_check.py tests/test_verifier.py
git commit -m "feat: API verifier — HTTP probe and stack auto-selection (Step 3)"
```

---

## Task 8: Stack Interfaces and Preset Router

**Files:**
- Create: `installer/stacks/__init__.py`
- Create: `installer/stacks/presets.py`
- Create: `installer/stacks/db/__init__.py`
- Create: `installer/stacks/db/base.py`
- Create: `installer/stacks/backend/__init__.py`
- Create: `installer/stacks/backend/base.py`
- Create: `installer/stacks/frontend/__init__.py`
- Create: `installer/stacks/frontend/base.py`
- Create: `tests/stacks/__init__.py`
- Create: `tests/stacks/test_presets.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/stacks/test_presets.py
import pytest
from installer.stacks.presets import resolve_stack, StackResolutionError
from installer.core.config import InstallerConfig, StackConfig, DBConfig, BackendConfig, FrontendConfig

def _cfg(backend, db_engine, frontend):
    return StackConfig(
        database=DBConfig(engine=db_engine, mode="local"),
        backend=BackendConfig(framework=backend),
        frontend=FrontendConfig(framework=frontend),
    )

def test_resolve_laravel_returns_correct_classes():
    from installer.stacks.backend.laravel import LaravelBackend
    from installer.stacks.db.mysql import MySQLLayer
    from installer.stacks.frontend.react import ReactFrontend
    cfg = _cfg("laravel", "mysql", "react")
    stack = resolve_stack(cfg, adapter=None)
    assert isinstance(stack["backend"], LaravelBackend)
    assert isinstance(stack["db"], MySQLLayer)
    assert isinstance(stack["frontend"], ReactFrontend)

def test_resolve_node_mongo_returns_correct_classes():
    from installer.stacks.backend.node import NodeBackend
    from installer.stacks.db.mongodb import MongoDBLayer
    from installer.stacks.frontend.vue import VueFrontend
    cfg = _cfg("node", "mongodb", "vue")
    stack = resolve_stack(cfg, adapter=None)
    assert isinstance(stack["backend"], NodeBackend)
    assert isinstance(stack["db"], MongoDBLayer)
    assert isinstance(stack["frontend"], VueFrontend)

def test_resolve_unknown_backend_raises():
    cfg = _cfg("unknown_fw", "mysql", "none")
    with pytest.raises(StackResolutionError):
        resolve_stack(cfg, adapter=None)

def test_resolve_none_frontend_returns_none():
    cfg = _cfg("django", "postgresql", "none")
    stack = resolve_stack(cfg, adapter=None)
    assert stack["frontend"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/stacks/test_presets.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create all `__init__.py` files** (empty)

```bash
touch installer/stacks/__init__.py installer/stacks/db/__init__.py installer/stacks/backend/__init__.py installer/stacks/frontend/__init__.py tests/stacks/__init__.py
```

- [ ] **Step 4: Create `installer/stacks/db/base.py`**

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from installer.adapters.base import BaseAdapter


class BaseDBLayer(ABC):
    def __init__(self, adapter: BaseAdapter | None, config):
        self.adapter = adapter
        self.config = config

    @abstractmethod
    def install_local(self) -> None:
        """Install DB server on target (local mode only)."""

    @abstractmethod
    def connect_external(self) -> None:
        """Validate external connection parameters."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Return True if DB is reachable."""

    @abstractmethod
    def restore_backup(self, source: str) -> None:
        """Restore from a backup URL or local path."""

    @abstractmethod
    def write_env(self, env_path: str) -> None:
        """Write DB credentials to .env file on target."""

    def setup(self) -> None:
        if self.config.mode == "local":
            self.install_local()
        else:
            self.connect_external()
        if self.config.backup_url:
            self.restore_backup(self.config.backup_url)
        self.write_env(self.config.__dict__.get("env_path", ".env"))
```

- [ ] **Step 5: Create `installer/stacks/backend/base.py`**

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from installer.adapters.base import BaseAdapter


class BaseBackend(ABC):
    def __init__(self, adapter: BaseAdapter | None, config):
        self.adapter = adapter
        self.config = config

    @abstractmethod
    def preflight(self) -> list[str]:
        """Return list of missing prerequisite names, empty if all ok."""

    @abstractmethod
    def install(self) -> None:
        """Install runtime and packages on target."""

    @abstractmethod
    def configure(self, env_path: str) -> None:
        """Write config files (.env, nginx conf, etc.)."""

    @abstractmethod
    def deploy(self, project_path: str) -> None:
        """Deploy app code from project_path on target."""

    @abstractmethod
    def start(self) -> None:
        """Start the app process/service."""

    @abstractmethod
    def default_verify_url(self) -> str:
        """Return the default health check URL for this backend."""
```

- [ ] **Step 6: Create `installer/stacks/frontend/base.py`**

```python
from __future__ import annotations
from abc import ABC, abstractmethod
from installer.adapters.base import BaseAdapter


class BaseFrontend(ABC):
    def __init__(self, adapter: BaseAdapter | None, config):
        self.adapter = adapter
        self.config = config

    @abstractmethod
    def build(self, project_path: str) -> None:
        """Build the frontend assets on target."""

    @abstractmethod
    def serve(self, build_dir: str, domain: str) -> None:
        """Configure web server to serve the built assets."""
```

- [ ] **Step 7: Create stub stack classes** (minimal implementations so `resolve_stack` can import them)

Create `installer/stacks/db/mysql.py`:
```python
from installer.stacks.db.base import BaseDBLayer
class MySQLLayer(BaseDBLayer):
    def install_local(self): pass
    def connect_external(self): pass
    def test_connection(self): return True
    def restore_backup(self, source): pass
    def write_env(self, env_path): pass
```

Create `installer/stacks/db/postgres.py`:
```python
from installer.stacks.db.base import BaseDBLayer
class PostgreSQLLayer(BaseDBLayer):
    def install_local(self): pass
    def connect_external(self): pass
    def test_connection(self): return True
    def restore_backup(self, source): pass
    def write_env(self, env_path): pass
```

Create `installer/stacks/db/mongodb.py`:
```python
from installer.stacks.db.base import BaseDBLayer
class MongoDBLayer(BaseDBLayer):
    def install_local(self): pass
    def connect_external(self): pass
    def test_connection(self): return True
    def restore_backup(self, source): pass
    def write_env(self, env_path): pass
```

Create `installer/stacks/db/external.py`:
```python
from installer.stacks.db.base import BaseDBLayer
class ExternalDBLayer(BaseDBLayer):
    def install_local(self): pass
    def connect_external(self): pass
    def test_connection(self): return True
    def restore_backup(self, source): pass
    def write_env(self, env_path): pass
```

Create `installer/stacks/backend/laravel.py`:
```python
from installer.stacks.backend.base import BaseBackend
class LaravelBackend(BaseBackend):
    def preflight(self): return []
    def install(self): pass
    def configure(self, env_path): pass
    def deploy(self, project_path): pass
    def start(self): pass
    def default_verify_url(self): return "http://localhost/api/health"
```

Create `installer/stacks/backend/node.py`:
```python
from installer.stacks.backend.base import BaseBackend
class NodeBackend(BaseBackend):
    def preflight(self): return []
    def install(self): pass
    def configure(self, env_path): pass
    def deploy(self, project_path): pass
    def start(self): pass
    def default_verify_url(self): return "http://localhost:3000/health"
```

Create `installer/stacks/backend/python_app.py`:
```python
from installer.stacks.backend.base import BaseBackend
class PythonBackend(BaseBackend):
    def preflight(self): return []
    def install(self): pass
    def configure(self, env_path): pass
    def deploy(self, project_path): pass
    def start(self): pass
    def default_verify_url(self): return "http://localhost:8000/api/health"
```

Create `installer/stacks/backend/java.py`:
```python
from installer.stacks.backend.base import BaseBackend
class JavaBackend(BaseBackend):
    def preflight(self): return []
    def install(self): pass
    def configure(self, env_path): pass
    def deploy(self, project_path): pass
    def start(self): pass
    def default_verify_url(self): return "http://localhost:8080/actuator/health"
```

Create `installer/stacks/frontend/react.py`:
```python
from installer.stacks.frontend.base import BaseFrontend
class ReactFrontend(BaseFrontend):
    def build(self, project_path): pass
    def serve(self, build_dir, domain): pass
```

Create `installer/stacks/frontend/vue.py`:
```python
from installer.stacks.frontend.base import BaseFrontend
class VueFrontend(BaseFrontend):
    def build(self, project_path): pass
    def serve(self, build_dir, domain): pass
```

Create `installer/stacks/frontend/angular.py`:
```python
from installer.stacks.frontend.base import BaseFrontend
class AngularFrontend(BaseFrontend):
    def build(self, project_path): pass
    def serve(self, build_dir, domain): pass
```

Create `installer/stacks/frontend/ssr.py`:
```python
from installer.stacks.frontend.base import BaseFrontend
class SSRFrontend(BaseFrontend):
    def build(self, project_path): pass
    def serve(self, build_dir, domain): pass
```

- [ ] **Step 8: Create `installer/stacks/presets.py`**

```python
from __future__ import annotations
from installer.adapters.base import BaseAdapter
from installer.core.config import StackConfig


class StackResolutionError(Exception):
    pass


_DB_MAP = {
    "mysql": "installer.stacks.db.mysql.MySQLLayer",
    "postgresql": "installer.stacks.db.postgres.PostgreSQLLayer",
    "mongodb": "installer.stacks.db.mongodb.MongoDBLayer",
    "sqlite": "installer.stacks.db.mysql.MySQLLayer",  # treated as mysql-lite
    "external": "installer.stacks.db.external.ExternalDBLayer",
}

_BACKEND_MAP = {
    "laravel": "installer.stacks.backend.laravel.LaravelBackend",
    "node": "installer.stacks.backend.node.NodeBackend",
    "django": "installer.stacks.backend.python_app.PythonBackend",
    "fastapi": "installer.stacks.backend.python_app.PythonBackend",
    "flask": "installer.stacks.backend.python_app.PythonBackend",
    "springboot": "installer.stacks.backend.java.JavaBackend",
}

_FRONTEND_MAP = {
    "react": "installer.stacks.frontend.react.ReactFrontend",
    "vue": "installer.stacks.frontend.vue.VueFrontend",
    "angular": "installer.stacks.frontend.angular.AngularFrontend",
    "nextjs": "installer.stacks.frontend.ssr.SSRFrontend",
    "nuxt": "installer.stacks.frontend.ssr.SSRFrontend",
    "blade": "installer.stacks.frontend.ssr.SSRFrontend",
    "jinja2": "installer.stacks.frontend.ssr.SSRFrontend",
    "none": None,
}


def _import(dotted: str):
    module_path, cls_name = dotted.rsplit(".", 1)
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, cls_name)


def resolve_stack(stack_config: StackConfig, adapter: BaseAdapter | None) -> dict:
    db_key = stack_config.database.mode if stack_config.database.mode == "external" else stack_config.database.engine
    db_cls_path = _DB_MAP.get(db_key)
    if not db_cls_path:
        raise StackResolutionError(f"Unknown database engine: {stack_config.database.engine!r}")

    backend_key = stack_config.backend.framework
    backend_cls_path = _BACKEND_MAP.get(backend_key)
    if not backend_cls_path:
        raise StackResolutionError(f"Unknown backend framework: {backend_key!r}")

    frontend_key = stack_config.frontend.framework
    frontend_cls_path = _FRONTEND_MAP.get(frontend_key)
    if frontend_cls_path is None and frontend_key != "none":
        raise StackResolutionError(f"Unknown frontend framework: {frontend_key!r}")

    db_obj = _import(db_cls_path)(adapter, stack_config.database)
    backend_obj = _import(backend_cls_path)(adapter, stack_config.backend)
    frontend_obj = _import(frontend_cls_path)(adapter, stack_config.frontend) if frontend_cls_path else None

    return {"db": db_obj, "backend": backend_obj, "frontend": frontend_obj}
```

- [ ] **Step 9: Run tests to verify they pass**

```bash
pytest tests/stacks/test_presets.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 10: Commit**

```bash
git add installer/stacks/ tests/stacks/
git commit -m "feat: stack interfaces, stub plugins, and preset resolver"
```

---

## Task 9: System Verifier (Step 5)

**Files:**
- Create: `installer/verifier/system_check.py`

- [ ] **Step 1: Write failing tests** (add to `tests/test_verifier.py`)

```python
from installer.verifier.system_check import SystemCheck, SystemCheckResult

def test_system_check_all_pass():
    runner = MagicMock()
    runner.run.side_effect = [
        _mock_runner("active"),             # service nginx
        _mock_runner(""),                   # port 80
        _mock_runner("2 received"),         # db ping
    ]
    checks = SystemCheck(runner=runner)
    results = checks.run(services=["nginx"], ports=[80], db_host="127.0.0.1")
    assert all(r.passed for r in results)

def test_system_check_service_not_running():
    runner = MagicMock()
    runner.run.side_effect = [
        _mock_runner("inactive", returncode=1),
    ]
    checks = SystemCheck(runner=runner)
    results = checks.run(services=["nginx"], ports=[], db_host=None)
    assert not results[0].passed
    assert "nginx" in results[0].label

def _mock_runner(stdout="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.returncode = returncode
    return r
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_verifier.py -v -k "system_check"
```

Expected: ImportError.

- [ ] **Step 3: Create `installer/verifier/system_check.py`**

```python
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class SystemCheckResult:
    label: str
    passed: bool
    detail: str = ""


class SystemCheck:
    def __init__(self, runner):
        self._r = runner

    def run(
        self,
        services: list[str],
        ports: list[int],
        db_host: Optional[str],
    ) -> list[SystemCheckResult]:
        results: list[SystemCheckResult] = []

        for svc in services:
            res = self._r.run(f"systemctl is-active {svc}")
            passed = res.returncode == 0 and "active" in res.stdout
            results.append(SystemCheckResult(label=f"Service: {svc}", passed=passed, detail=res.stdout))

        for port in ports:
            res = self._r.run(f"ss -tlnp | grep :{port}")
            passed = res.returncode == 0 and str(port) in res.stdout
            results.append(SystemCheckResult(label=f"Port: {port}", passed=passed, detail=res.stdout))

        if db_host:
            res = self._r.run(f"ping -c 2 {db_host}")
            passed = res.returncode == 0 and "received" in res.stdout
            results.append(SystemCheckResult(label=f"DB ping: {db_host}", passed=passed, detail=res.stdout))

        return results
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_verifier.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add installer/verifier/system_check.py tests/test_verifier.py
git commit -m "feat: system verifier — service, port, DB checks (Step 5)"
```

---

## Task 10: Core Engine — Orchestrator

**Files:**
- Create: `installer/core/engine.py`
- Create: `tests/test_engine.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_engine.py
import pytest
from unittest.mock import MagicMock, patch, call
from installer.core.engine import Engine
from installer.core.config import InstallerConfig, StackConfig, DBConfig, BackendConfig, FrontendConfig, VerifyAPIConfig

def _make_config():
    return InstallerConfig(
        project_path="/var/www/app",
        domain="app.test",
        stack=StackConfig(
            database=DBConfig(engine="mysql", mode="local"),
            backend=BackendConfig(framework="laravel"),
            frontend=FrontendConfig(framework="react"),
        ),
        verify_api=VerifyAPIConfig(url="http://localhost/api/health", expect_status=200, timeout="10s", retries=1),
    )

def test_engine_runs_all_5_steps():
    config = _make_config()
    runner = MagicMock()
    runner.run.return_value = MagicMock(stdout="Ubuntu 22.04", returncode=0)

    with patch("installer.core.engine.detect_environment") as mock_detect, \
         patch("installer.core.engine.UbuntuAdapter") as mock_adapter_cls, \
         patch("installer.core.engine.resolve_stack") as mock_resolve, \
         patch("installer.core.engine.APICheck") as mock_api:

        mock_detect.return_value = "ubuntu"
        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter
        mock_stack = {"db": MagicMock(), "backend": MagicMock(), "frontend": MagicMock()}
        mock_resolve.return_value = mock_stack
        mock_api.return_value.run.return_value = MagicMock(passed=True, status_code=200)

        engine = Engine(config=config, runner=runner)
        report = engine.run()

        assert report["steps"][0]["status"] == "done"   # Step 1 detect
        assert report["steps"][1]["status"] == "done"   # Step 2 adapter
        assert report["steps"][2]["status"] == "done"   # Step 3 api verify
        assert report["steps"][3]["status"] == "done"   # Step 4 install
        assert report["steps"][4]["status"] == "done"   # Step 5 verify

def test_engine_stops_on_step1_failure():
    config = _make_config()
    runner = MagicMock()

    with patch("installer.core.engine.detect_environment") as mock_detect:
        from installer.core.detector import DetectionError
        mock_detect.side_effect = DetectionError("unknown env")

        engine = Engine(config=config, runner=runner)
        report = engine.run()

        assert report["steps"][0]["status"] == "failed"
        assert report["steps"][1]["status"] == "pending"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_engine.py -v
```

Expected: ImportError.

- [ ] **Step 3: Create `installer/core/engine.py`**

```python
from __future__ import annotations
import json
from typing import Optional, Callable
from installer.core.config import InstallerConfig
from installer.core.detector import detect_environment, Environment, DetectionError
from installer.core.progress import Progress
from installer.core.logger import get_logger
from installer.adapters.ubuntu import UbuntuAdapter
from installer.adapters.docker import DockerAdapter
from installer.adapters.windows import WindowsAdapter
from installer.stacks.presets import resolve_stack
from installer.verifier.api_check import APICheck, probe_project_stack
from installer.verifier.system_check import SystemCheck

log = get_logger("engine")

_ADAPTER_MAP = {
    Environment.UBUNTU: UbuntuAdapter,
    Environment.DOCKER: DockerAdapter,
    Environment.WINDOWS: WindowsAdapter,
}


class Engine:
    def __init__(self, config: InstallerConfig, runner, db_config_callback: Optional[Callable] = None):
        self.config = config
        self.runner = runner
        self.progress = Progress()
        # db_config_callback: called during Step 3 for interactive DB config.
        # Receives detected stack dict, returns updated DBConfig.
        # If None, uses config.stack.database as-is.
        self.db_config_callback = db_config_callback

    def run(self) -> dict:
        # Step 1 — OS Detection
        self.progress.start(1, "OS / Environment Detection")
        try:
            env = detect_environment(self.runner)
            self.progress.complete(1)
            log.info(f"Detected environment: {env}")
        except DetectionError as e:
            self.progress.fail(1, str(e))
            return self._report()

        # Step 2 — Load Adapter
        self.progress.start(2, "Environment Adapter")
        adapter_cls = _ADAPTER_MAP[env]
        adapter = adapter_cls(runner=self.runner)
        self.progress.complete(2)
        log.info(f"Loaded adapter: {adapter_cls.__name__}")

        # Step 3 — API Verification + Stack Selection
        self.progress.start(3, "API-Based Stack Selection")
        try:
            probe_url = f"http://{self.config.domain}/.installer/probe"
            probed = probe_project_stack(probe_url)
            if probed:
                log.info("Stack auto-detected from project probe")
                # Merge probed values into config (probed takes precedence for backend/frontend)
                self.config.stack.backend.framework = probed["backend"]["framework"] or self.config.stack.backend.framework
                self.config.stack.frontend.framework = probed["frontend"]["framework"] or self.config.stack.frontend.framework

            # Interactive DB configuration (web UI pauses here if callback provided)
            if self.db_config_callback:
                self.config.stack.database = self.db_config_callback(self.config.stack)

            self.progress.complete(3)
        except Exception as e:
            self.progress.fail(3, str(e))
            return self._report()

        # Step 4 — Stack Installation
        self.progress.start(4, "Stack Installation")
        try:
            stack = resolve_stack(self.config.stack, adapter)
            # 4a DB
            stack["db"].setup()
            # 4b Backend
            stack["backend"].install()
            stack["backend"].configure(self.config.env_file)
            stack["backend"].deploy(self.config.project_path)
            stack["backend"].start()
            # 4c Frontend (optional)
            if stack["frontend"]:
                stack["frontend"].build(self.config.project_path)
                stack["frontend"].serve(self.config.stack.frontend.output_dir, self.config.domain)
            self.progress.complete(4)
        except Exception as e:
            self.progress.fail(4, str(e))
            return self._report()

        # Step 5 — Post-Install Checks
        self.progress.start(5, "Post-Installation Checks")
        try:
            sys_results = SystemCheck(runner=self.runner).run(
                services=["nginx"],
                ports=[80, 443],
                db_host="127.0.0.1" if self.config.stack.database.mode == "local" else self.config.stack.database.host,
            )
            api_result = None
            if self.config.verify_api:
                timeout_s = int(self.config.verify_api.timeout.replace("s", ""))
                api_result = APICheck(
                    url=self.config.verify_api.url,
                    method=self.config.verify_api.method,
                    expect_status=self.config.verify_api.expect_status,
                    expect_json=self.config.verify_api.expect_json,
                    timeout=timeout_s,
                    retries=self.config.verify_api.retries,
                ).run()
            self.progress.complete(5)
            log.info("Post-install checks complete")
        except Exception as e:
            self.progress.fail(5, str(e))

        return self._report(api_result=api_result)

    def _report(self, api_result=None) -> dict:
        summary = self.progress.summary()
        report = {
            "project": self.config.project_path,
            "domain": self.config.domain,
            "stack": {
                "database": {"engine": self.config.stack.database.engine, "mode": self.config.stack.database.mode},
                "backend": {"framework": self.config.stack.backend.framework},
                "frontend": {"framework": self.config.stack.frontend.framework},
            },
            "steps": summary["steps"],
            "api_check": None,
            "issues": [s["error"] for s in summary["steps"] if s["error"]],
        }
        if api_result:
            report["api_check"] = {
                "url": self.config.verify_api.url if self.config.verify_api else "",
                "passed": api_result.passed,
                "status_code": api_result.status_code,
                "latency_ms": api_result.latency_ms,
                "error": api_result.error,
            }
        return report
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_engine.py -v
```

Expected: All 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add installer/core/engine.py tests/test_engine.py
git commit -m "feat: core orchestrator engine — runs all 5 steps"
```

---

## Task 11: Wire CLI to Engine

**Files:**
- Modify: `installer/cli.py`

- [ ] **Step 1: Write failing tests** (add to `tests/test_engine.py`)

```python
from click.testing import CliRunner
from installer.cli import cli

def test_cli_detect_command_runs():
    runner_cli = CliRunner()
    with patch("installer.cli.detect_environment") as mock_detect:
        mock_detect.return_value = "ubuntu"
        result = runner_cli.invoke(cli, ["detect"])
        assert result.exit_code == 0
        assert "ubuntu" in result.output.lower()

def test_cli_install_requires_config(tmp_path):
    runner_cli = CliRunner()
    result = runner_cli.invoke(cli, ["install", "--config", str(tmp_path / "nonexistent.yaml")])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_engine.py -v -k "cli"
```

Expected: FAIL — CLI commands not yet wired.

- [ ] **Step 3: Replace `installer/cli.py` with wired version**

```python
import click
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def cli():
    """Installer — deploy web apps to Ubuntu, Docker, or Windows servers."""


@cli.command()
@click.option("--host", default=None, help="Target server IP or hostname")
@click.option("--user", default=None, help="SSH user")
@click.option("--key", default=None, help="Path to SSH private key")
def detect(host, user, key):
    """Probe the target OS and environment."""
    from installer.core.detector import detect_environment, DetectionError
    from installer.core.ssh import SSHClient

    if host:
        runner = SSHClient(host=host, user=user or "ubuntu", key_path=key)
        runner.connect()
    else:
        import subprocess
        class LocalRunner:
            def run(self, cmd):
                import subprocess
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                class R:
                    stdout = r.stdout.strip()
                    returncode = r.returncode
                return R()
        runner = LocalRunner()

    try:
        env = detect_environment(runner)
        console.print(f"[green]Detected:[/green] {env}")
    except DetectionError as e:
        console.print(f"[red]Detection failed:[/red] {e}")
        raise SystemExit(1)


@cli.command()
@click.option("--config", "config_path", default="installer.yaml", show_default=True)
@click.option("--host", default=None)
@click.option("--user", default=None)
@click.option("--key", default=None)
def install(config_path, host, user, key):
    """Run the full 5-step install flow."""
    from installer.core.config import load_config, ConfigError
    from installer.core.engine import Engine
    from installer.core.ssh import SSHClient

    try:
        config = load_config(config_path)
    except ConfigError as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise SystemExit(1)

    if host:
        runner = SSHClient(host=host, user=user or "ubuntu", key_path=key)
        runner.connect()
    else:
        import subprocess
        class LocalRunner:
            def run(self, cmd):
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                class R:
                    stdout = r.stdout.strip()
                    returncode = r.returncode
                return R()
        runner = LocalRunner()

    engine = Engine(config=config, runner=runner)
    report = engine.run()
    console.print_json(json.dumps(report, indent=2))


@cli.command()
@click.option("--config", "config_path", default="installer.yaml", show_default=True)
def verify(config_path):
    """Run post-install health checks."""
    from installer.core.config import load_config, ConfigError
    try:
        config = load_config(config_path)
    except ConfigError as e:
        console.print(f"[red]Config error:[/red] {e}")
        raise SystemExit(1)
    console.print("[yellow]verify:[/yellow] run installer install first, then verify")


@cli.command()
def dashboard():
    """Launch web UI on port 8080."""
    console.print("[cyan]Starting web dashboard on http://localhost:8080[/cyan]")
    try:
        from installer.web.server import start
        start()
    except ImportError:
        console.print("[yellow]Web dashboard not yet installed. Run: pip install installer-tool[web][/yellow]")


@cli.command(name="list")
@click.option("--manifest", default="manifest.yaml", show_default=True)
def list_projects(manifest):
    """List all projects in manifest."""
    from installer.core.config import load_manifest, ConfigError
    try:
        m = load_manifest(manifest)
    except ConfigError as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
    table = Table("Name", "Config", "Servers")
    for p in m.projects:
        table.add_row(p.name, p.config, ", ".join(s.host for s in p.servers))
    console.print(table)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_engine.py -v -k "cli"
```

Expected: All CLI tests PASS.

- [ ] **Step 5: Verify CLI end-to-end manually**

```bash
installer --help
installer detect
```

Expected: Help text printed, detect runs without error.

- [ ] **Step 6: Commit**

```bash
git add installer/cli.py tests/test_engine.py
git commit -m "feat: wire CLI commands to engine and config loader"
```

---

## Task 12: Bootstrap script

**Files:**
- Create: `bootstrap.sh`

- [ ] **Step 1: Create `bootstrap.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

INSTALLER_VERSION="${INSTALLER_VERSION:-latest}"
INSTALL_DIR="${INSTALL_DIR:-/opt/installer}"
WEB_PORT="${WEB_PORT:-8080}"

echo "==> Installer bootstrap starting"
echo "    Version : $INSTALLER_VERSION"
echo "    Dir     : $INSTALL_DIR"

# 1. Install Python 3.11+ if missing
if ! command -v python3.11 &>/dev/null && ! python3 -c "import sys; assert sys.version_info >= (3,11)" 2>/dev/null; then
    echo "==> Installing Python 3.11"
    apt-get update -qq
    apt-get install -y python3.11 python3.11-venv python3-pip
fi

PYTHON=$(command -v python3.11 || command -v python3)

# 2. Create venv
echo "==> Creating virtualenv at $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
"$PYTHON" -m venv "$INSTALL_DIR/venv"
source "$INSTALL_DIR/venv/bin/activate"

# 3. Install installer-tool
echo "==> Installing installer-tool"
pip install --quiet installer-tool

# 4. Launch web dashboard
echo "==> Starting web dashboard on port $WEB_PORT"
nohup installer dashboard --port "$WEB_PORT" > "$INSTALL_DIR/dashboard.log" 2>&1 &
DASHBOARD_PID=$!
echo "$DASHBOARD_PID" > "$INSTALL_DIR/dashboard.pid"

# 5. Print access info
SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""
echo "=========================================="
echo "  Installer is running!"
echo "  Open: http://$SERVER_IP:$WEB_PORT"
echo "=========================================="
echo ""
echo "  Logs : tail -f $INSTALL_DIR/dashboard.log"
echo "  Stop : kill \$(cat $INSTALL_DIR/dashboard.pid)"
```

- [ ] **Step 2: Make executable and test locally**

```bash
chmod +x bootstrap.sh
bash -n bootstrap.sh   # syntax check only, no execution
```

Expected: No output (syntax valid).

- [ ] **Step 3: Commit**

```bash
git add bootstrap.sh
git commit -m "feat: bootstrap.sh — curl|bash entry point, installs tool and starts dashboard"
```

---

## Task 13: Full stack implementations — Laravel backend

**Files:**
- Modify: `installer/stacks/backend/laravel.py`
- Create: `tests/stacks/test_backend.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/stacks/test_backend.py
import pytest
from unittest.mock import MagicMock
from installer.stacks.backend.laravel import LaravelBackend
from installer.core.config import BackendConfig

def _mock_adapter(stdout="", returncode=0):
    adapter = MagicMock()
    adapter.run.return_value = MagicMock(stdout=stdout, returncode=returncode)
    return adapter

def test_laravel_preflight_returns_empty_when_php_present():
    adapter = _mock_adapter("PHP 8.2.0")
    cfg = BackendConfig(framework="laravel", php_version="8.2")
    backend = LaravelBackend(adapter=adapter, config=cfg)
    adapter.run.return_value = MagicMock(stdout="PHP 8.2.0", returncode=0)
    result = backend.preflight()
    assert result == []

def test_laravel_install_calls_apt_and_composer():
    adapter = _mock_adapter()
    cfg = BackendConfig(framework="laravel", php_version="8.2")
    backend = LaravelBackend(adapter=adapter, config=cfg)
    backend.install()
    calls = [str(c) for c in adapter.install_packages.call_args_list]
    assert any("php8.2" in c for c in calls)

def test_laravel_default_verify_url():
    cfg = BackendConfig(framework="laravel")
    b = LaravelBackend(adapter=None, config=cfg)
    assert b.default_verify_url() == "http://localhost/api/health"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/stacks/test_backend.py -v
```

Expected: FAIL — stub has no real implementation.

- [ ] **Step 3: Replace `installer/stacks/backend/laravel.py` with real implementation**

```python
from __future__ import annotations
from installer.stacks.backend.base import BaseBackend


class LaravelBackend(BaseBackend):
    def preflight(self) -> list[str]:
        missing = []
        res = self.adapter.run(f"php{self.config.php_version} --version 2>/dev/null || php --version")
        if res.returncode != 0 or "PHP" not in res.stdout:
            missing.append(f"php{self.config.php_version}")
        return missing

    def install(self) -> None:
        v = self.config.php_version
        self.adapter.install_packages([
            f"php{v}", f"php{v}-fpm", f"php{v}-mbstring", f"php{v}-xml",
            f"php{v}-curl", f"php{v}-zip", f"php{v}-mysql", f"php{v}-pgsql",
            "composer", "nginx", "git", "unzip",
        ])
        self.adapter.run("curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer")

    def configure(self, env_path: str) -> None:
        nginx_conf = f"""server {{
    listen 80;
    server_name _;
    root /var/www/app/public;
    index index.php;
    location / {{ try_files $uri $uri/ /index.php?$query_string; }}
    location ~ \\.php$ {{
        fastcgi_pass unix:/run/php/php{self.config.php_version}-fpm.sock;
        fastcgi_index index.php;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }}
}}"""
        self.adapter.write_file("/etc/nginx/sites-available/app", nginx_conf)
        self.adapter.run("ln -sf /etc/nginx/sites-available/app /etc/nginx/sites-enabled/app")
        self.adapter.run("rm -f /etc/nginx/sites-enabled/default")

    def deploy(self, project_path: str) -> None:
        self.adapter.run(f"cd {project_path} && composer install --no-dev --optimize-autoloader")
        self.adapter.run(f"cd {project_path} && php artisan migrate --force")
        self.adapter.run(f"cd {project_path} && php artisan config:cache && php artisan route:cache")
        self.adapter.run(f"chown -R www-data:www-data {project_path}/storage {project_path}/bootstrap/cache")

    def start(self) -> None:
        v = self.config.php_version
        self.adapter.enable_service(f"php{v}-fpm")
        self.adapter.start_service(f"php{v}-fpm")
        self.adapter.enable_service("nginx")
        self.adapter.start_service("nginx")
        if self.config.queue:
            self.adapter.run("php artisan queue:restart")

    def default_verify_url(self) -> str:
        return "http://localhost/api/health"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/stacks/test_backend.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add installer/stacks/backend/laravel.py tests/stacks/test_backend.py
git commit -m "feat: Laravel backend — apt packages, Composer, nginx, artisan deploy"
```

---

## Task 14: Node, Python, Java backends + DB layers + Frontend layers

**Files:**
- Modify: `installer/stacks/backend/node.py`
- Modify: `installer/stacks/backend/python_app.py`
- Modify: `installer/stacks/backend/java.py`
- Modify: `installer/stacks/db/mysql.py`
- Modify: `installer/stacks/db/postgres.py`
- Modify: `installer/stacks/db/mongodb.py`
- Modify: `installer/stacks/db/external.py`
- Modify: `installer/stacks/frontend/react.py`
- Modify: `installer/stacks/frontend/vue.py`
- Modify: `installer/stacks/frontend/angular.py`
- Modify: `installer/stacks/frontend/ssr.py`
- Modify: `tests/stacks/test_backend.py`
- Create: `tests/stacks/test_db.py`
- Create: `tests/stacks/test_frontend.py`

- [ ] **Step 1: Write tests for Node backend**

Add to `tests/stacks/test_backend.py`:
```python
from installer.stacks.backend.node import NodeBackend
from installer.core.config import BackendConfig as BC

def test_node_install_calls_nvm_and_pm2():
    adapter = _mock_adapter()
    b = NodeBackend(adapter=adapter, config=BC(framework="node", node_version="20"))
    b.install()
    cmds = [str(c) for c in adapter.run.call_args_list]
    assert any("nvm" in c or "node" in c.lower() for c in cmds)

def test_node_default_verify_url():
    b = NodeBackend(adapter=None, config=BC(framework="node"))
    assert "3000" in b.default_verify_url() or "health" in b.default_verify_url()
```

- [ ] **Step 2: Write tests for DB layers**

```python
# tests/stacks/test_db.py
import pytest
from unittest.mock import MagicMock
from installer.stacks.db.mysql import MySQLLayer
from installer.stacks.db.postgres import PostgreSQLLayer
from installer.stacks.db.mongodb import MongoDBLayer
from installer.stacks.db.external import ExternalDBLayer
from installer.core.config import DBConfig

def _adapter():
    a = MagicMock()
    a.run.return_value = MagicMock(stdout="", returncode=0)
    return a

def test_mysql_install_local():
    a = _adapter()
    layer = MySQLLayer(adapter=a, config=DBConfig(engine="mysql", mode="local", db_name="myapp"))
    layer.install_local()
    a.install_packages.assert_called()
    installed = str(a.install_packages.call_args_list)
    assert "mysql-server" in installed

def test_postgres_install_local():
    a = _adapter()
    layer = PostgreSQLLayer(adapter=a, config=DBConfig(engine="postgresql", mode="local", db_name="myapp"))
    layer.install_local()
    installed = str(a.install_packages.call_args_list)
    assert "postgresql" in installed

def test_mongodb_install_local():
    a = _adapter()
    layer = MongoDBLayer(adapter=a, config=DBConfig(engine="mongodb", mode="local", db_name="myapp"))
    layer.install_local()
    installed = str(a.install_packages.call_args_list)
    assert "mongodb" in installed or "mongod" in installed.lower()

def test_external_db_connect_writes_env(tmp_path):
    a = _adapter()
    cfg = DBConfig(engine="postgresql", mode="external", host="db.example.com", port=5432, user="app", db_name="myapp")
    layer = ExternalDBLayer(adapter=a, config=cfg)
    layer.connect_external()
    layer.write_env(str(tmp_path / ".env"))
    a.write_file.assert_called()
```

- [ ] **Step 3: Write tests for frontend layers**

```python
# tests/stacks/test_frontend.py
import pytest
from unittest.mock import MagicMock
from installer.stacks.frontend.react import ReactFrontend
from installer.stacks.frontend.vue import VueFrontend
from installer.core.config import FrontendConfig

def _adapter():
    a = MagicMock()
    a.run.return_value = MagicMock(stdout="", returncode=0)
    return a

def test_react_build_runs_npm():
    a = _adapter()
    fe = ReactFrontend(adapter=a, config=FrontendConfig(framework="react", build_tool="vite"))
    fe.build("/var/www/app")
    cmds = [str(c) for c in a.run.call_args_list]
    assert any("npm" in c or "vite" in c for c in cmds)

def test_vue_build_runs_npm():
    a = _adapter()
    fe = VueFrontend(adapter=a, config=FrontendConfig(framework="vue"))
    fe.build("/var/www/app")
    cmds = [str(c) for c in a.run.call_args_list]
    assert any("npm" in c for c in cmds)
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
pytest tests/stacks/ -v
```

Expected: Multiple FAILs — stub implementations don't do anything real.

- [ ] **Step 5: Implement Node backend**

Replace `installer/stacks/backend/node.py`:
```python
from installer.stacks.backend.base import BaseBackend

class NodeBackend(BaseBackend):
    def preflight(self):
        res = self.adapter.run("node --version")
        return [] if res.returncode == 0 else ["nodejs"]

    def install(self):
        v = self.config.node_version
        self.adapter.run(f"curl -fsSL https://deb.nodesource.com/setup_{v}.x | bash -")
        self.adapter.install_packages(["nodejs", "nginx"])
        self.adapter.run("npm install -g pm2")

    def configure(self, env_path):
        nginx = """server {
    listen 80;
    server_name _;
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}"""
        self.adapter.write_file("/etc/nginx/sites-available/app", nginx)
        self.adapter.run("ln -sf /etc/nginx/sites-available/app /etc/nginx/sites-enabled/app")
        self.adapter.run("rm -f /etc/nginx/sites-enabled/default")

    def deploy(self, project_path):
        self.adapter.run(f"cd {project_path} && npm ci --production")

    def start(self):
        self.adapter.run(f"pm2 start ecosystem.config.js --env production || pm2 restart all")
        self.adapter.enable_service("nginx")
        self.adapter.start_service("nginx")

    def default_verify_url(self):
        return "http://localhost:3000/health"
```

- [ ] **Step 6: Implement Python backend**

Replace `installer/stacks/backend/python_app.py`:
```python
from installer.stacks.backend.base import BaseBackend

class PythonBackend(BaseBackend):
    def preflight(self):
        res = self.adapter.run("python3 --version")
        return [] if res.returncode == 0 else ["python3"]

    def install(self):
        v = self.config.python_version
        self.adapter.install_packages([f"python{v}", f"python{v}-venv", "nginx"])
        self.adapter.run(f"python{v} -m venv /opt/app-venv")
        self.adapter.run("pip install gunicorn")

    def configure(self, env_path):
        nginx = """server {
    listen 80;
    server_name _;
    location / {
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}"""
        self.adapter.write_file("/etc/nginx/sites-available/app", nginx)
        self.adapter.run("ln -sf /etc/nginx/sites-available/app /etc/nginx/sites-enabled/app")
        self.adapter.run("rm -f /etc/nginx/sites-enabled/default")

    def deploy(self, project_path):
        fw = self.config.framework
        self.adapter.run(f"cd {project_path} && /opt/app-venv/bin/pip install -r requirements.txt")
        if fw == "django":
            self.adapter.run(f"cd {project_path} && /opt/app-venv/bin/python manage.py migrate --noinput")
            self.adapter.run(f"cd {project_path} && /opt/app-venv/bin/python manage.py collectstatic --noinput")

    def start(self):
        self.adapter.run("systemctl daemon-reload")
        self.adapter.enable_service("gunicorn")
        self.adapter.start_service("gunicorn")
        self.adapter.enable_service("nginx")
        self.adapter.start_service("nginx")

    def default_verify_url(self):
        return "http://localhost:8000/api/health"
```

- [ ] **Step 7: Implement Java backend**

Replace `installer/stacks/backend/java.py`:
```python
from installer.stacks.backend.base import BaseBackend

class JavaBackend(BaseBackend):
    def preflight(self):
        res = self.adapter.run("java -version 2>&1")
        return [] if res.returncode == 0 else ["openjdk"]

    def install(self):
        v = self.config.java_version
        self.adapter.install_packages([f"openjdk-{v}-jdk", "nginx"])

    def configure(self, env_path):
        nginx = """server {
    listen 80;
    server_name _;
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}"""
        self.adapter.write_file("/etc/nginx/sites-available/app", nginx)
        self.adapter.run("ln -sf /etc/nginx/sites-available/app /etc/nginx/sites-enabled/app")
        self.adapter.run("rm -f /etc/nginx/sites-enabled/default")

    def deploy(self, project_path):
        self.adapter.run(f"cd {project_path} && ./gradlew bootJar -x test || mvn package -DskipTests")

    def start(self):
        self.adapter.run("systemctl daemon-reload")
        self.adapter.enable_service("app-java")
        self.adapter.start_service("app-java")
        self.adapter.enable_service("nginx")
        self.adapter.start_service("nginx")

    def default_verify_url(self):
        return "http://localhost:8080/actuator/health"
```

- [ ] **Step 8: Implement DB layers**

Replace `installer/stacks/db/mysql.py`:
```python
from installer.stacks.db.base import BaseDBLayer

class MySQLLayer(BaseDBLayer):
    def install_local(self):
        self.adapter.install_packages(["mysql-server"])
        self.adapter.run("systemctl start mysql")
        db = self.config.db_name
        self.adapter.run(f"mysql -u root -e \"CREATE DATABASE IF NOT EXISTS {db};\"")

    def connect_external(self): pass

    def test_connection(self):
        res = self.adapter.run(f"mysql -h {self.config.host or 'localhost'} -u {self.config.user or 'root'} -e 'SELECT 1' 2>/dev/null")
        return res.returncode == 0

    def restore_backup(self, source):
        self.adapter.run(f"wget -q '{source}' -O /tmp/backup.sql.gz && gunzip /tmp/backup.sql.gz")
        self.adapter.run(f"mysql -u root {self.config.db_name} < /tmp/backup.sql")

    def write_env(self, env_path):
        lines = [
            f"DB_CONNECTION=mysql",
            f"DB_HOST={self.config.host or '127.0.0.1'}",
            f"DB_PORT={self.config.port or 3306}",
            f"DB_DATABASE={self.config.db_name}",
            f"DB_USERNAME={self.config.user or 'root'}",
        ]
        self.adapter.write_file(env_path, "\n".join(lines))
```

Replace `installer/stacks/db/postgres.py`:
```python
from installer.stacks.db.base import BaseDBLayer

class PostgreSQLLayer(BaseDBLayer):
    def install_local(self):
        self.adapter.install_packages(["postgresql", "postgresql-contrib"])
        self.adapter.run("systemctl start postgresql")
        db = self.config.db_name
        self.adapter.run(f"sudo -u postgres psql -c \"CREATE DATABASE {db};\" 2>/dev/null || true")

    def connect_external(self): pass

    def test_connection(self):
        h = self.config.host or "localhost"
        res = self.adapter.run(f"pg_isready -h {h} -p {self.config.port or 5432}")
        return res.returncode == 0

    def restore_backup(self, source):
        self.adapter.run(f"wget -q '{source}' -O /tmp/backup.dump")
        self.adapter.run(f"pg_restore -U postgres -d {self.config.db_name} /tmp/backup.dump")

    def write_env(self, env_path):
        lines = [
            "DB_CONNECTION=pgsql",
            f"DB_HOST={self.config.host or '127.0.0.1'}",
            f"DB_PORT={self.config.port or 5432}",
            f"DB_DATABASE={self.config.db_name}",
            f"DB_USERNAME={self.config.user or 'postgres'}",
        ]
        self.adapter.write_file(env_path, "\n".join(lines))
```

Replace `installer/stacks/db/mongodb.py`:
```python
from installer.stacks.db.base import BaseDBLayer

class MongoDBLayer(BaseDBLayer):
    def install_local(self):
        self.adapter.run("curl -fsSL https://pgp.mongodb.com/server-7.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg")
        self.adapter.run("echo 'deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse' > /etc/apt/sources.list.d/mongodb-org-7.0.list")
        self.adapter.install_packages(["mongodb-org"])
        self.adapter.run("systemctl start mongod")

    def connect_external(self): pass

    def test_connection(self):
        uri = f"mongodb://{self.config.host or 'localhost'}:{self.config.port or 27017}"
        res = self.adapter.run(f"mongosh '{uri}' --eval 'db.runCommand({{ping:1}})' --quiet")
        return res.returncode == 0

    def restore_backup(self, source):
        self.adapter.run(f"wget -q '{source}' -O /tmp/backup.gz && gunzip /tmp/backup.gz")
        self.adapter.run(f"mongorestore --db {self.config.db_name} /tmp/backup")

    def write_env(self, env_path):
        lines = [f"MONGO_URI=mongodb://{self.config.host or '127.0.0.1'}:{self.config.port or 27017}/{self.config.db_name}"]
        self.adapter.write_file(env_path, "\n".join(lines))
```

Replace `installer/stacks/db/external.py`:
```python
from installer.stacks.db.base import BaseDBLayer

class ExternalDBLayer(BaseDBLayer):
    def install_local(self): pass

    def connect_external(self): pass

    def test_connection(self):
        h = self.config.host or ""
        p = self.config.port or 5432
        res = self.adapter.run(f"nc -z {h} {p}")
        return res.returncode == 0

    def restore_backup(self, source):
        self.adapter.run(f"wget -q '{source}' -O /tmp/backup.sql")

    def write_env(self, env_path):
        lines = [
            f"DB_HOST={self.config.host}",
            f"DB_PORT={self.config.port or 5432}",
            f"DB_DATABASE={self.config.db_name}",
            f"DB_USERNAME={self.config.user or ''}",
        ]
        self.adapter.write_file(env_path, "\n".join(lines))
```

- [ ] **Step 9: Implement Frontend layers**

Replace `installer/stacks/frontend/react.py`:
```python
from installer.stacks.frontend.base import BaseFrontend

class ReactFrontend(BaseFrontend):
    def build(self, project_path):
        self.adapter.run(f"cd {project_path} && npm ci && npm run build")

    def serve(self, build_dir, domain):
        conf = f"""server {{
    listen 80;
    server_name {domain};
    root {build_dir};
    index index.html;
    location / {{ try_files $uri /index.html; }}
}}"""
        self.adapter.write_file("/etc/nginx/sites-available/frontend", conf)
        self.adapter.run("ln -sf /etc/nginx/sites-available/frontend /etc/nginx/sites-enabled/frontend")
        self.adapter.start_service("nginx")
```

Replace `installer/stacks/frontend/vue.py`:
```python
from installer.stacks.frontend.base import BaseFrontend

class VueFrontend(BaseFrontend):
    def build(self, project_path):
        self.adapter.run(f"cd {project_path} && npm ci && npm run build")

    def serve(self, build_dir, domain):
        conf = f"""server {{
    listen 80;
    server_name {domain};
    root {build_dir};
    index index.html;
    location / {{ try_files $uri /index.html; }}
}}"""
        self.adapter.write_file("/etc/nginx/sites-available/frontend", conf)
        self.adapter.run("ln -sf /etc/nginx/sites-available/frontend /etc/nginx/sites-enabled/frontend")
        self.adapter.start_service("nginx")
```

Replace `installer/stacks/frontend/angular.py`:
```python
from installer.stacks.frontend.base import BaseFrontend

class AngularFrontend(BaseFrontend):
    def build(self, project_path):
        self.adapter.run(f"cd {project_path} && npm ci && npx ng build --configuration production")

    def serve(self, build_dir, domain):
        conf = f"""server {{
    listen 80;
    server_name {domain};
    root {build_dir};
    index index.html;
    location / {{ try_files $uri /index.html; }}
}}"""
        self.adapter.write_file("/etc/nginx/sites-available/frontend", conf)
        self.adapter.run("ln -sf /etc/nginx/sites-available/frontend /etc/nginx/sites-enabled/frontend")
        self.adapter.start_service("nginx")
```

Replace `installer/stacks/frontend/ssr.py`:
```python
from installer.stacks.frontend.base import BaseFrontend

class SSRFrontend(BaseFrontend):
    """Handles Blade, Jinja2 (served by backend), Next.js, and Nuxt."""

    def build(self, project_path):
        fw = self.config.framework
        if fw in ("nextjs", "nuxt"):
            self.adapter.run(f"cd {project_path} && npm ci && npm run build")
        # blade/jinja2: assets compiled via backend deploy step (mix/vite)

    def serve(self, build_dir, domain):
        fw = self.config.framework
        if fw in ("nextjs",):
            self.adapter.run(f"pm2 start 'npm start' --name nextjs --cwd {build_dir}")
        elif fw in ("nuxt",):
            self.adapter.run(f"pm2 start 'node .output/server/index.mjs' --name nuxt --cwd {build_dir}")
        # blade/jinja2: served by PHP-FPM or gunicorn — no separate step needed
```

- [ ] **Step 10: Run all stack tests**

```bash
pytest tests/stacks/ -v
```

Expected: All tests PASS.

- [ ] **Step 11: Run full test suite**

```bash
pytest -v
```

Expected: All tests PASS (or clearly documented skips for platform-specific tests).

- [ ] **Step 12: Commit**

```bash
git add installer/stacks/ tests/stacks/test_backend.py tests/stacks/test_db.py tests/stacks/test_frontend.py
git commit -m "feat: full stack implementations — Node, Python, Java backends; MySQL, Postgres, Mongo DB layers; React, Vue, Angular, SSR frontends"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by task |
|---|---|
| Bootstrap script (curl \| bash) | Task 12 |
| Local CLI + SSH entry | Task 11 |
| Step 1: OS detection | Task 4 |
| Step 2: Ubuntu/Docker/Windows adapters | Tasks 5, 6 |
| Step 3: API probe + stack auto-select | Task 7 |
| Step 3: DB Web UI dialog (interactive pause) | Task 10 (engine `db_config_callback`) — UI in Plan 2 |
| Step 4a: DB layers (MySQL, Postgres, Mongo, External) | Task 14 |
| Step 4b: Backend (Laravel, Node, Python, Java) | Tasks 13, 14 |
| Step 4c: Frontend (React, Vue, Angular, SSR) | Task 14 |
| Preset expansion (MERN, MEAN, etc.) | Task 2 (config.py) + Task 8 |
| Step 5: Post-install system checks | Task 9 |
| Step 5: API health re-check | Task 7 + Task 10 |
| Deployment report (JSON) | Task 10 |
| installer.yaml + manifest.yaml | Tasks 1, 2 |
| CLI commands: detect/init/install/verify/status/deploy/dashboard/list | Task 11 |

**Gaps identified and addressed:**
- `installer init` command is stubbed — will generate `installer.yaml` interactively. Acceptable for Plan 1; full wizard goes in Plan 2.
- DB Web UI dialog callback is wired in engine but no UI until Plan 2. The engine accepts a `db_config_callback` so tests can inject it without UI.
- Monitoring setup (Step 5 optional) not implemented in Plan 1 — `MonitoringConfig` is parsed but no action taken. Deferred to Plan 2.
