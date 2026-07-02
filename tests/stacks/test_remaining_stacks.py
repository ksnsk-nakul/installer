from unittest.mock import MagicMock

import pytest

from installer.stacks.backend.node import NodeBackend
from installer.stacks.backend.python_app import PythonBackend
from installer.stacks.backend.java import JavaBackend
from installer.stacks.db.mysql import MySQLLayer
from installer.stacks.db.postgres import PostgresLayer
from installer.stacks.db.mongodb import MongoDBLayer
from installer.stacks.db.external import ExternalDBLayer
from installer.stacks.frontend.react import ReactFrontend
from installer.stacks.frontend.vue import VueFrontend
from installer.stacks.frontend.angular import AngularFrontend
from installer.stacks.frontend.ssr import SSRFrontend


def make_adapter(run_output=""):
    adapter = MagicMock()
    adapter.run.return_value = run_output
    return adapter


def run_calls(adapter):
    return [c.args[0] for c in adapter.run.call_args_list]


# ════════════════════════════════════════════════════════════════════════════
# Node backend
# ════════════════════════════════════════════════════════════════════════════

def test_node_install_installs_nodejs_and_pm2():
    adapter = make_adapter()
    b = NodeBackend(adapter, {})
    b.install()
    cmds = run_calls(adapter)
    assert any("nodesource" in c for c in cmds)
    assert any("pm2" in c for c in cmds)
    pkgs = adapter.install_packages.call_args_list
    assert any("nodejs" in str(p) for p in pkgs)


def test_node_configure_writes_nginx_conf():
    adapter = make_adapter()
    b = NodeBackend(adapter, {"_domain": "node.test"})
    b.configure()
    paths = [c.args[0] for c in adapter.write_file.call_args_list]
    assert any("nginx" in p for p in paths)


def test_node_deploy_runs_npm_install():
    adapter = make_adapter()
    b = NodeBackend(adapter, {})
    b.deploy("/var/www/nodeapp")
    assert any("npm install" in c for c in run_calls(adapter))


def test_node_start_runs_pm2():
    adapter = make_adapter()
    b = NodeBackend(adapter, {"_project_path": "/var/www/app"})
    b.start()
    assert any("pm2 start" in c for c in run_calls(adapter))
    adapter.start_service.assert_any_call("nginx")


# ════════════════════════════════════════════════════════════════════════════
# Python backend
# ════════════════════════════════════════════════════════════════════════════

def test_python_install_packages_include_venv():
    adapter = make_adapter()
    b = PythonBackend(adapter, {"framework": "django", "python_version": "3.11"})
    b.install()
    pkgs_calls = [str(c) for c in adapter.install_packages.call_args_list]
    assert any("python3.11-venv" in s for s in pkgs_calls)


def test_python_configure_writes_gunicorn_service():
    adapter = make_adapter()
    b = PythonBackend(adapter, {"framework": "django", "_project_path": "/var/www/app"})
    b.configure()
    paths = [c.args[0] for c in adapter.write_file.call_args_list]
    assert any("gunicorn.service" in p for p in paths)


def test_python_asgi_uses_uvicorn_worker():
    adapter = make_adapter()
    b = PythonBackend(adapter, {"framework": "fastapi", "_project_path": "/var/www/app"})
    b.configure()
    contents = [c.args[1] for c in adapter.write_file.call_args_list]
    assert any("UvicornWorker" in c for c in contents)


def test_python_deploy_creates_venv():
    adapter = make_adapter()
    b = PythonBackend(adapter, {"framework": "django", "python_version": "3.11"})
    b.deploy("/var/www/pyapp")
    assert any("venv" in c for c in run_calls(adapter))


def test_python_django_runs_migrate():
    adapter = make_adapter()
    b = PythonBackend(adapter, {"framework": "django"})
    b.deploy("/var/www/pyapp")
    assert any("migrate" in c for c in run_calls(adapter))


def test_python_start_enables_gunicorn():
    adapter = make_adapter()
    b = PythonBackend(adapter, {"framework": "django"})
    b.start()
    adapter.enable_service.assert_any_call("gunicorn")
    adapter.start_service.assert_any_call("gunicorn")


# ════════════════════════════════════════════════════════════════════════════
# Java backend
# ════════════════════════════════════════════════════════════════════════════

def test_java_install_includes_openjdk():
    adapter = make_adapter()
    b = JavaBackend(adapter, {"java_version": "17"})
    b.install()
    pkgs_calls = [str(c) for c in adapter.install_packages.call_args_list]
    assert any("openjdk-17-jdk" in s for s in pkgs_calls)


def test_java_configure_writes_springboot_service():
    adapter = make_adapter()
    b = JavaBackend(adapter, {"_domain": "spring.test", "_project_path": "/var/www/app"})
    b.configure()
    paths = [c.args[0] for c in adapter.write_file.call_args_list]
    assert any("springboot.service" in p for p in paths)


def test_java_deploy_maven_build():
    adapter = make_adapter()
    b = JavaBackend(adapter, {"build_tool": "maven"})
    b.deploy("/var/www/javaapp")
    assert any("mvn package" in c for c in run_calls(adapter))


def test_java_deploy_gradle_build():
    adapter = make_adapter()
    b = JavaBackend(adapter, {"build_tool": "gradle"})
    b.deploy("/var/www/javaapp")
    assert any("gradlew bootJar" in c for c in run_calls(adapter))


def test_java_start_enables_springboot():
    adapter = make_adapter()
    b = JavaBackend(adapter, {})
    b.start()
    adapter.enable_service.assert_any_call("springboot")
    adapter.start_service.assert_any_call("springboot")


# ════════════════════════════════════════════════════════════════════════════
# MySQL DB layer
# ════════════════════════════════════════════════════════════════════════════

def test_mysql_install_local_installs_package():
    adapter = make_adapter("mysqld is alive")
    db = MySQLLayer(adapter, {"db_name": "mydb", "user": "myuser", "password": "secret"})
    db.install_local()
    pkgs = [str(c) for c in adapter.install_packages.call_args_list]
    assert any("mysql-server" in p for p in pkgs)
    adapter.start_service.assert_any_call("mysql")


def test_mysql_test_connection_true():
    adapter = make_adapter("mysqld is alive")
    db = MySQLLayer(adapter, {})
    assert db.test_connection() is True


def test_mysql_test_connection_false():
    adapter = make_adapter("error connecting")
    db = MySQLLayer(adapter, {})
    assert db.test_connection() is False


def test_mysql_write_env():
    adapter = make_adapter()
    db = MySQLLayer(adapter, {"db_name": "mydb", "user": "usr", "password": "pw", "host": "db.host"})
    db.write_env("/var/www/.env")
    content = adapter.write_file.call_args.args[1]
    assert "DB_CONNECTION=mysql" in content
    assert "DB_HOST=db.host" in content


def test_mysql_restore_backup_local_file():
    adapter = make_adapter()
    db = MySQLLayer(adapter, {"db_name": "mydb", "user": "root"})
    db.restore_backup("/tmp/backup.sql")
    assert any("/tmp/backup.sql" in c for c in run_calls(adapter))


# ════════════════════════════════════════════════════════════════════════════
# PostgreSQL DB layer
# ════════════════════════════════════════════════════════════════════════════

def test_postgres_install_local():
    adapter = make_adapter()
    db = PostgresLayer(adapter, {})
    db.install_local()
    pkgs = [str(c) for c in adapter.install_packages.call_args_list]
    assert any("postgresql" in p for p in pkgs)
    adapter.start_service.assert_any_call("postgresql")


def test_postgres_test_connection_true():
    adapter = make_adapter("accepting connections")
    db = PostgresLayer(adapter, {})
    assert db.test_connection() is True


def test_postgres_write_env():
    adapter = make_adapter()
    db = PostgresLayer(adapter, {"db_name": "pgdb", "user": "pguser", "password": "pw", "host": "pg.host"})
    db.write_env("/var/www/.env")
    content = adapter.write_file.call_args.args[1]
    assert "DB_CONNECTION=pgsql" in content
    assert "pg.host" in content


# ════════════════════════════════════════════════════════════════════════════
# MongoDB DB layer
# ════════════════════════════════════════════════════════════════════════════

def test_mongodb_install_local():
    adapter = make_adapter()
    db = MongoDBLayer(adapter, {})
    db.install_local()
    pkgs = [str(c) for c in adapter.install_packages.call_args_list]
    assert any("mongodb-org" in p for p in pkgs)
    adapter.start_service.assert_any_call("mongod")


def test_mongodb_test_connection_true():
    adapter = make_adapter("{ ok: 1 }")
    db = MongoDBLayer(adapter, {})
    assert db.test_connection() is True


def test_mongodb_write_env():
    adapter = make_adapter()
    db = MongoDBLayer(adapter, {"db_name": "mydb", "user": "usr", "password": "pw", "host": "mongo.host"})
    db.write_env("/var/www/.env")
    content = adapter.write_file.call_args.args[1]
    assert "MONGODB_URI" in content
    assert "mongo.host" in content


# ════════════════════════════════════════════════════════════════════════════
# External DB layer
# ════════════════════════════════════════════════════════════════════════════

def test_external_install_local_raises():
    adapter = make_adapter()
    db = ExternalDBLayer(adapter, {})
    with pytest.raises(NotImplementedError):
        db.install_local()


def test_external_connect_requires_host():
    adapter = make_adapter()
    db = ExternalDBLayer(adapter, {"engine": "postgresql"})
    with pytest.raises(ValueError, match="host"):
        db.connect_external()


def test_external_test_connection_mysql():
    adapter = make_adapter("mysqld is alive")
    db = ExternalDBLayer(adapter, {"engine": "mysql", "host": "db.host"})
    assert db.test_connection() is True


def test_external_write_env_postgresql():
    adapter = make_adapter()
    db = ExternalDBLayer(adapter, {
        "engine": "postgresql", "host": "pg.host", "db_name": "mydb",
        "user": "usr", "password": "pw",
    })
    db.write_env("/var/www/.env")
    content = adapter.write_file.call_args.args[1]
    assert "DB_CONNECTION=pgsql" in content


# ════════════════════════════════════════════════════════════════════════════
# Frontend layers
# ════════════════════════════════════════════════════════════════════════════

def test_react_build_runs_npm_build():
    adapter = make_adapter()
    f = ReactFrontend(adapter, {})
    f.build("/var/www/app")
    assert any("npm run build" in c for c in run_calls(adapter))


def test_react_serve_writes_nginx_conf():
    adapter = make_adapter()
    f = ReactFrontend(adapter, {"_domain": "react.test", "_project_path": "/var/www/app"})
    f.serve()
    paths = [c.args[0] for c in adapter.write_file.call_args_list]
    assert any("nginx" in p for p in paths)


def test_vue_build_runs_npm_build():
    adapter = make_adapter()
    f = VueFrontend(adapter, {})
    f.build("/var/www/vueapp")
    assert any("npm run build" in c for c in run_calls(adapter))


def test_angular_build_runs_ng_build():
    adapter = make_adapter()
    f = AngularFrontend(adapter, {})
    f.build("/var/www/ngapp")
    assert any("ng build" in c for c in run_calls(adapter))


def test_ssr_blade_build_is_noop():
    adapter = make_adapter()
    f = SSRFrontend(adapter, {"framework": "blade"})
    f.build("/var/www/laravelapp")
    adapter.run.assert_not_called()


def test_ssr_blade_serve_is_noop():
    adapter = make_adapter()
    f = SSRFrontend(adapter, {"framework": "blade"})
    f.serve()
    adapter.run.assert_not_called()
    adapter.write_file.assert_not_called()


def test_ssr_next_build_runs_npm_build():
    adapter = make_adapter()
    f = SSRFrontend(adapter, {"framework": "next"})
    f.build("/var/www/nextapp")
    assert any("npm run build" in c for c in run_calls(adapter))


def test_ssr_next_serve_starts_pm2():
    adapter = make_adapter()
    f = SSRFrontend(adapter, {"framework": "next", "_domain": "next.test", "_project_path": "/var/www/app"})
    f.serve()
    assert any("pm2 start" in c for c in run_calls(adapter))
    adapter.start_service.assert_any_call("nginx")
