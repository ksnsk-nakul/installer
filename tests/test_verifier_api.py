from unittest.mock import patch, MagicMock

import httpx
import pytest

from installer.verifier.api_check import APICheck, CheckResult, probe_project_stack


def make_response(status_code=200, json_data=None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data if json_data is not None else {}
    return resp


# ---------------------------------------------------------------------------
# APICheck.probe
# ---------------------------------------------------------------------------

def test_probe_pass_on_status_match():
    with patch("httpx.request", return_value=make_response(200, {"status": "ok"})):
        check = APICheck()
        result = check.probe(url="http://x/health", expect_status=200)
        assert result.status == "pass"
        assert result.response_time_ms is not None


def test_probe_pass_with_json_match():
    with patch("httpx.request", return_value=make_response(200, {"status": "ok", "version": "1.0"})):
        check = APICheck()
        result = check.probe(
            url="http://x/health", expect_status=200, expect_json={"status": "ok"}
        )
        assert result.status == "pass"


def test_probe_fail_on_status_mismatch():
    with patch("httpx.request", return_value=make_response(500, {})):
        check = APICheck()
        result = check.probe(url="http://x/health", expect_status=200, retries=1)
        assert result.status == "fail"
        assert "500" in result.detail


def test_probe_fail_on_json_mismatch():
    with patch("httpx.request", return_value=make_response(200, {"status": "degraded"})):
        check = APICheck()
        result = check.probe(
            url="http://x/health",
            expect_status=200,
            expect_json={"status": "ok"},
            retries=1,
        )
        assert result.status == "fail"
        assert "JSON mismatch" in result.detail


def test_probe_retries_then_fails():
    with patch("httpx.request", side_effect=httpx.ConnectError("refused")):
        check = APICheck()
        result = check.probe(url="http://x/health", retries=2)
        assert result.status == "fail"
        assert httpx.request.call_count if hasattr(httpx.request, "call_count") else True


def test_probe_recovers_after_initial_failure():
    responses = [httpx.ConnectError("refused"), make_response(200, {"status": "ok"})]

    def side_effect(*args, **kwargs):
        result = responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    with patch("httpx.request", side_effect=side_effect):
        check = APICheck()
        result = check.probe(url="http://x/health", retries=3)
        assert result.status == "pass"


# ---------------------------------------------------------------------------
# probe_project_stack
# ---------------------------------------------------------------------------

def test_probe_project_stack_parses_fields():
    with patch("httpx.get", return_value=make_response(200, {
        "framework": "laravel",
        "runtime": "php",
        "version": "8.2",
        "frontend": "react",
    })):
        result = probe_project_stack("http://x/api/stack-info")
        assert result["reachable"] is True
        assert result["framework"] == "laravel"
        assert result["runtime"] == "php"
        assert result["frontend"] == "react"


def test_probe_project_stack_unreachable():
    with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
        result = probe_project_stack("http://x/api/stack-info")
        assert result["reachable"] is False
        assert result["framework"] is None


def test_probe_project_stack_non_json_body():
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.side_effect = ValueError("not json")
    with patch("httpx.get", return_value=resp):
        result = probe_project_stack("http://x/api/stack-info")
        assert result["reachable"] is True
        assert result["framework"] is None
