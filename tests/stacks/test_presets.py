from unittest.mock import MagicMock

import pytest

from installer.core.config import StackConfig, DatabaseConfig, BackendConfig, FrontendConfig
from installer.stacks.presets import resolve_stack, UnknownStackComponentError, ResolvedStack
from installer.stacks.db.mongodb import MongoDBLayer
from installer.stacks.db.mysql import MySQLLayer
from installer.stacks.db.external import ExternalDBLayer
from installer.stacks.backend.node import NodeBackend
from installer.stacks.backend.laravel import LaravelBackend
from installer.stacks.frontend.react import ReactFrontend
from installer.stacks.frontend.base import NoneFrontend


def make_adapter():
    return MagicMock()


def test_resolve_mern_stack():
    config = StackConfig(
        database=DatabaseConfig(engine="mongodb", mode="local"),
        backend=BackendConfig(framework="node"),
        frontend=FrontendConfig(framework="react"),
    )
    resolved = resolve_stack(config, make_adapter())
    assert isinstance(resolved, ResolvedStack)
    assert isinstance(resolved.db, MongoDBLayer)
    assert isinstance(resolved.backend, NodeBackend)
    assert isinstance(resolved.frontend, ReactFrontend)


def test_resolve_external_db_overrides_engine_choice():
    config = StackConfig(
        database=DatabaseConfig(engine="mysql", mode="external", host="db.example.com"),
        backend=BackendConfig(framework="laravel"),
        frontend=FrontendConfig(framework=None),
    )
    resolved = resolve_stack(config, make_adapter())
    assert isinstance(resolved.db, ExternalDBLayer)
    assert isinstance(resolved.backend, LaravelBackend)


def test_resolve_no_frontend_uses_none_frontend():
    config = StackConfig(
        database=DatabaseConfig(engine="mysql", mode="local"),
        backend=BackendConfig(framework="java"),
        frontend=FrontendConfig(framework=None),
    )
    resolved = resolve_stack(config, make_adapter())
    assert isinstance(resolved.frontend, NoneFrontend)


def test_resolve_unknown_backend_raises():
    config = StackConfig(
        database=DatabaseConfig(engine="mysql", mode="local"),
        backend=BackendConfig(framework="cobol"),
        frontend=FrontendConfig(framework=None),
    )
    with pytest.raises(UnknownStackComponentError, match="backend framework"):
        resolve_stack(config, make_adapter())


def test_resolve_unknown_db_engine_raises():
    config = StackConfig(
        database=DatabaseConfig(engine="oracle", mode="local"),
        backend=BackendConfig(framework="node"),
        frontend=FrontendConfig(framework=None),
    )
    with pytest.raises(UnknownStackComponentError, match="database engine"):
        resolve_stack(config, make_adapter())


def test_resolve_unknown_frontend_raises():
    config = StackConfig(
        database=DatabaseConfig(engine="mysql", mode="local"),
        backend=BackendConfig(framework="laravel"),
        frontend=FrontendConfig(framework="svelte"),
    )
    with pytest.raises(UnknownStackComponentError, match="frontend framework"):
        resolve_stack(config, make_adapter())


def test_db_layer_receives_config_dict():
    config = StackConfig(
        database=DatabaseConfig(engine="postgresql", mode="local", db_name="mydb"),
        backend=BackendConfig(framework="django"),
        frontend=FrontendConfig(framework=None),
    )
    resolved = resolve_stack(config, make_adapter())
    assert resolved.db.config["db_name"] == "mydb"


def test_base_db_layer_setup_dispatches_local():
    from installer.stacks.db.base import BaseDBLayer

    calls = []

    class FakeDB(BaseDBLayer):
        def install_local(self):
            calls.append("local")

        def connect_external(self):
            calls.append("external")

        def test_connection(self):
            return True

        def restore_backup(self, source):
            calls.append(f"restore:{source}")

        def write_env(self, env_path):
            calls.append(f"env:{env_path}")

    db = FakeDB(make_adapter(), {"mode": "local"})
    db.setup()
    assert calls == ["local"]


def test_base_db_layer_setup_dispatches_external_with_backup():
    from installer.stacks.db.base import BaseDBLayer

    calls = []

    class FakeDB(BaseDBLayer):
        def install_local(self):
            calls.append("local")

        def connect_external(self):
            calls.append("external")

        def test_connection(self):
            return True

        def restore_backup(self, source):
            calls.append(f"restore:{source}")

        def write_env(self, env_path):
            calls.append(f"env:{env_path}")

    db = FakeDB(make_adapter(), {"mode": "external", "backup_url": "http://x/backup.sql"})
    db.setup()
    assert calls == ["external", "restore:http://x/backup.sql"]


def test_base_backend_run_all_order():
    from installer.stacks.backend.base import BaseBackend

    calls = []

    class FakeBackend(BaseBackend):
        def preflight(self):
            calls.append("preflight")

        def install(self):
            calls.append("install")

        def configure(self):
            calls.append("configure")

        def deploy(self, path):
            calls.append(f"deploy:{path}")

        def start(self):
            calls.append("start")

    backend = FakeBackend(make_adapter(), {})
    backend.run_all("/var/www/app")
    assert calls == ["preflight", "install", "configure", "deploy:/var/www/app", "start"]


def test_base_frontend_run_all_order():
    from installer.stacks.frontend.base import BaseFrontend

    calls = []

    class FakeFrontend(BaseFrontend):
        def build(self, project_path):
            calls.append(f"build:{project_path}")

        def serve(self):
            calls.append("serve")

    frontend = FakeFrontend(make_adapter(), {})
    frontend.run_all("/var/www/app")
    assert calls == ["build:/var/www/app", "serve"]


def test_none_frontend_noop():
    frontend = NoneFrontend(make_adapter(), {})
    frontend.build("/var/www/app")
    frontend.serve()  # should not raise
