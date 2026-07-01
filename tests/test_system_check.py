from unittest.mock import MagicMock, patch

import pytest

from installer.verifier.system_check import SystemCheck, SystemCheckResult


def runner_with(return_value="", raises=None):
    r = MagicMock()
    if raises:
        r.run.side_effect = raises
    else:
        r.run.return_value = return_value
    return r


# ---------------------------------------------------------------------------
# check_service
# ---------------------------------------------------------------------------

def test_check_service_pass_on_active():
    sc = SystemCheck()
    result = sc.check_service(runner_with("active"), "nginx")
    assert result.status == "pass"
    assert result.name == "service:nginx"


def test_check_service_pass_on_running():
    sc = SystemCheck()
    result = sc.check_service(runner_with("nginx is running"), "nginx")
    assert result.status == "pass"


def test_check_service_fail_on_inactive():
    sc = SystemCheck()
    result = sc.check_service(runner_with("inactive"), "nginx")
    assert result.status == "fail"
    assert result.fix_hint is not None


def test_check_service_fail_on_exception():
    sc = SystemCheck()
    result = sc.check_service(runner_with(raises=RuntimeError("ssh err")), "nginx")
    assert result.status == "fail"


# ---------------------------------------------------------------------------
# check_port
# ---------------------------------------------------------------------------

def test_check_port_pass_when_port_open():
    sc = SystemCheck()
    result = sc.check_port(runner_with("LISTEN 0.0.0.0:80"), 80)
    assert result.status == "pass"


def test_check_port_fail_when_empty():
    sc = SystemCheck()
    result = sc.check_port(runner_with(""), 80)
    assert result.status == "fail"
    assert result.fix_hint is not None


def test_check_port_fail_on_exception():
    sc = SystemCheck()
    result = sc.check_port(runner_with(raises=RuntimeError("timeout")), 443)
    assert result.status == "fail"


# ---------------------------------------------------------------------------
# check_ssl
# ---------------------------------------------------------------------------

def test_check_ssl_pass_with_date():
    sc = SystemCheck()
    out = "notBefore=Jun  1 00:00:00 2026 GMT\nnotAfter=Sep  1 00:00:00 2026 GMT"
    result = sc.check_ssl(runner_with(out), "example.com")
    assert result.status == "pass"
    assert "Sep" in result.detail


def test_check_ssl_warn_on_empty_output():
    sc = SystemCheck()
    result = sc.check_ssl(runner_with(""), "example.com")
    assert result.status == "warn"


def test_check_ssl_warn_on_exception():
    sc = SystemCheck()
    result = sc.check_ssl(runner_with(raises=RuntimeError("openssl not found")), "example.com")
    assert result.status == "warn"


# ---------------------------------------------------------------------------
# check_db_connectivity
# ---------------------------------------------------------------------------

def test_check_mysql_alive():
    sc = SystemCheck()
    result = sc.check_db_connectivity(runner_with("mysqld is alive"), "mysql", {})
    assert result.status == "pass"


def test_check_postgres_ready():
    sc = SystemCheck()
    result = sc.check_db_connectivity(runner_with("accepting connections"), "postgresql", {})
    assert result.status == "pass"


def test_check_mongodb_ok():
    sc = SystemCheck()
    result = sc.check_db_connectivity(runner_with("{ ok: 1 }"), "mongodb", {})
    assert result.status == "pass"


def test_check_db_fail_on_no_match():
    sc = SystemCheck()
    result = sc.check_db_connectivity(runner_with("error: connection refused"), "mysql", {})
    assert result.status == "fail"


# ---------------------------------------------------------------------------
# run() + summary()
# ---------------------------------------------------------------------------

def test_run_returns_results_for_all_checks():
    sc = SystemCheck()
    r = MagicMock()
    r.run.return_value = "active"
    results = sc.run(r, services=["nginx"], ports=[80])
    assert len(results) == 2


def test_summary_counts_correctly():
    results = [
        SystemCheckResult("a", "pass"),
        SystemCheckResult("b", "fail"),
        SystemCheckResult("c", "warn"),
        SystemCheckResult("d", "pass"),
    ]
    s = SystemCheck.summary(results)
    assert s["pass"] == 2
    assert s["fail"] == 1
    assert s["warn"] == 1


def test_run_empty_noop():
    sc = SystemCheck()
    results = sc.run(MagicMock())
    assert results == []
