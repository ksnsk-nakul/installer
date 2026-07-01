from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone

import pytest

from installer.core.engine import Engine, EngineError
from installer.core.config import (
    InstallerConfig, StackConfig, DatabaseConfig, BackendConfig, FrontendConfig
)


UBUNTU_OS_RELEASE = """
NAME="Ubuntu"
ID=ubuntu
ID_LIKE=debian
VERSION_ID="22.04"
""".strip()


def make_runner(outputs: dict[str, str] = None):
    runner = MagicMock()
    outputs = outputs or {}

    def run_side_effect(cmd: str) -> str:
        for key, val in outputs.items():
            if key in cmd:
                return val
        return ""

    runner.run.side_effect = run_side_effect
    return runner


def minimal_config(**overrides) -> InstallerConfig:
    defaults = dict(
        project_path="/var/www/app",
        domain="app.com",
        stack=StackConfig(
            database=DatabaseConfig(engine="mysql", mode="local"),
            backend=BackendConfig(framework="laravel"),
            frontend=FrontendConfig(framework=None),
        ),
    )
    defaults.update(overrides)
    return InstallerConfig(**defaults)


def ubuntu_runner():
    return make_runner({
        "ver": "",
        "/.dockerenv": "no",
        "/proc/1/cgroup": "",
        "/etc/os-release": UBUNTU_OS_RELEASE,
    })


def test_engine_runs_5_steps_and_returns_report():
    runner = ubuntu_runner()
    config = minimal_config()
    engine = Engine(config, runner)

    # Patch the parts that would actually SSH/install things
    with patch.object(engine, "_load_adapter") as mock_adapter_loader, \
         patch("installer.core.engine.resolve_stack") as mock_resolve:
        mock_adapter = MagicMock()
        mock_adapter_loader.return_value = mock_adapter

        mock_resolved = MagicMock()
        mock_resolve.return_value = mock_resolved

        with patch("installer.core.engine.SystemCheck") as mock_sc:
            mock_sc.return_value.run.return_value = []
            mock_sc.summary.return_value = {"pass": 0, "warn": 0, "fail": 0}

            report = engine.run()

    assert "steps" in report
    step_nums = [s["step"] for s in report["steps"] if s["step"] > 0]
    assert step_nums == [1, 2, 3, 4, 5]


def test_engine_report_contains_stack_info():
    runner = ubuntu_runner()
    config = minimal_config()
    engine = Engine(config, runner)

    with patch.object(engine, "_load_adapter") as mock_adapter_loader, \
         patch("installer.core.engine.resolve_stack") as mock_resolve, \
         patch("installer.core.engine.SystemCheck") as mock_sc:
        mock_adapter_loader.return_value = MagicMock()
        mock_resolve.return_value = MagicMock()
        mock_sc.return_value.run.return_value = []
        mock_sc.summary.return_value = {"pass": 0, "warn": 0, "fail": 0}

        report = engine.run()

    assert report["stack"]["database"]["engine"] == "mysql"
    assert report["stack"]["backend"]["framework"] == "laravel"


def test_engine_raises_on_unknown_env():
    runner = make_runner({"ver": "", "/etc/os-release": "", "uname": ""})
    config = minimal_config()
    engine = Engine(config, runner)

    with pytest.raises(EngineError, match="Unsupported environment"):
        engine.run()


def test_engine_calls_db_config_callback():
    runner = ubuntu_runner()
    called_with = {}

    def db_callback(db_cfg: dict) -> dict:
        called_with.update(db_cfg)
        return db_cfg

    config = minimal_config()
    engine = Engine(config, runner, db_config_callback=db_callback)

    with patch.object(engine, "_load_adapter") as mock_adapter_loader, \
         patch("installer.core.engine.resolve_stack") as mock_resolve, \
         patch("installer.core.engine.SystemCheck") as mock_sc:
        mock_adapter_loader.return_value = MagicMock()
        mock_resolve.return_value = MagicMock()
        mock_sc.return_value.run.return_value = []
        mock_sc.summary.return_value = {"pass": 0, "warn": 0, "fail": 0}

        engine.run()

    assert called_with.get("engine") == "mysql"


def test_engine_loads_ubuntu_adapter_for_ubuntu_env():
    from installer.core.detector import Environment
    from installer.adapters.ubuntu import UbuntuAdapter

    runner = ubuntu_runner()
    config = minimal_config()
    engine = Engine(config, runner)
    adapter = engine._load_adapter(Environment.UBUNTU)
    assert isinstance(adapter, UbuntuAdapter)


def test_engine_loads_windows_adapter_for_windows_env():
    from installer.core.detector import Environment
    from installer.adapters.windows import WindowsAdapter

    runner = MagicMock()
    config = minimal_config()
    engine = Engine(config, runner)
    adapter = engine._load_adapter(Environment.WINDOWS)
    assert isinstance(adapter, WindowsAdapter)
