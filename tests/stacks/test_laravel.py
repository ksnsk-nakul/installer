from unittest.mock import MagicMock, call

import pytest

from installer.stacks.backend.laravel import LaravelBackend


def make_adapter():
    adapter = MagicMock()
    adapter.run.return_value = ""
    return adapter


def make_backend(config: dict | None = None) -> LaravelBackend:
    return LaravelBackend(make_adapter(), config or {})


# ── php_version ───────────────────────────────────────────────────────────────

def test_default_php_version():
    b = make_backend()
    assert b.php_version == "8.2"


def test_custom_php_version():
    b = make_backend({"php_version": "8.3"})
    assert b.php_version == "8.3"


# ── preflight ─────────────────────────────────────────────────────────────────

def test_preflight_runs_uname():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {})
    b.preflight()
    adapter.run.assert_called_with("uname -s")


# ── install ───────────────────────────────────────────────────────────────────

def test_install_calls_apt_and_composer():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {"php_version": "8.2"})
    b.install()
    calls = [c.args[0] for c in adapter.run.call_args_list]
    assert any("apt-get update" in c for c in calls)
    assert any("composer" in c for c in calls)


def test_install_opens_ports():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {})
    b.install()
    adapter.open_port.assert_any_call(80, "tcp")
    adapter.open_port.assert_any_call(443, "tcp")


def test_install_includes_php_fpm():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {"php_version": "8.2"})
    b.install()
    pkgs = adapter.install_packages.call_args.args[0]
    assert "php8.2-fpm" in pkgs
    assert "nginx" in pkgs


# ── configure ─────────────────────────────────────────────────────────────────

def test_configure_writes_nginx_config():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {"_domain": "example.com", "_project_path": "/var/www/app"})
    b.configure()
    written_paths = [c.args[0] for c in adapter.write_file.call_args_list]
    assert any("nginx" in p for p in written_paths)


def test_configure_links_nginx_site():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {"_domain": "mysite.com"})
    b.configure()
    run_calls = [c.args[0] for c in adapter.run.call_args_list]
    assert any("sites-enabled/mysite.com" in c for c in run_calls)


def test_configure_queue_writes_systemd_unit():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {"queue": True, "_project_path": "/var/www/app"})
    b.configure()
    written_paths = [c.args[0] for c in adapter.write_file.call_args_list]
    assert any("laravel-queue.service" in p for p in written_paths)


def test_configure_no_queue_no_systemd_unit():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {"queue": False})
    b.configure()
    written_paths = [c.args[0] for c in adapter.write_file.call_args_list]
    assert not any("laravel-queue.service" in p for p in written_paths)


def test_configure_scheduler_writes_cron():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {"scheduler": True, "_project_path": "/var/www/app"})
    b.configure()
    written_paths = [c.args[0] for c in adapter.write_file.call_args_list]
    assert any("laravel-scheduler" in p for p in written_paths)


# ── deploy ────────────────────────────────────────────────────────────────────

def test_deploy_runs_composer_install():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {})
    b.deploy("/var/www/myapp")
    run_calls = [c.args[0] for c in adapter.run.call_args_list]
    assert any("composer install" in c for c in run_calls)


def test_deploy_runs_artisan_commands():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {})
    b.deploy("/var/www/myapp")
    run_calls = [c.args[0] for c in adapter.run.call_args_list]
    assert any("artisan key:generate" in c for c in run_calls)
    assert any("artisan migrate" in c for c in run_calls)
    assert any("artisan config:cache" in c for c in run_calls)


def test_deploy_sets_ownership():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {})
    b.deploy("/var/www/myapp")
    run_calls = [c.args[0] for c in adapter.run.call_args_list]
    assert any("chown -R www-data" in c for c in run_calls)


# ── start ─────────────────────────────────────────────────────────────────────

def test_start_enables_and_starts_services():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {"php_version": "8.2"})
    b.start()
    adapter.enable_service.assert_any_call("php8.2-fpm")
    adapter.start_service.assert_any_call("php8.2-fpm")
    adapter.enable_service.assert_any_call("nginx")
    adapter.start_service.assert_any_call("nginx")


def test_start_queue_worker_when_enabled():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {"queue": True})
    b.start()
    adapter.enable_service.assert_any_call("laravel-queue")
    adapter.start_service.assert_any_call("laravel-queue")


def test_start_no_queue_worker_when_disabled():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {"queue": False})
    b.start()
    enabled = [c.args[0] for c in adapter.enable_service.call_args_list]
    assert "laravel-queue" not in enabled


# ── run_all ───────────────────────────────────────────────────────────────────

def test_run_all_executes_all_steps():
    adapter = make_adapter()
    b = LaravelBackend(adapter, {"php_version": "8.2"})
    b.run_all("/var/www/myapp")
    # composer install from deploy, nginx from start
    run_calls = [c.args[0] for c in adapter.run.call_args_list]
    assert any("composer install" in c for c in run_calls)
    assert any("artisan migrate" in c for c in run_calls)
    adapter.start_service.assert_any_call("nginx")
