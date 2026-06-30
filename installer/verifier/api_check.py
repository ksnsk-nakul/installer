from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx


@dataclass
class CheckResult:
    name: str
    status: str  # "pass" | "warn" | "fail"
    detail: str = ""
    response_time_ms: Optional[float] = None
    raw: dict[str, Any] = field(default_factory=dict)


def _parse_timeout(timeout: str | int | float) -> float:
    """Accept '30s', '30', or numeric seconds."""
    if isinstance(timeout, (int, float)):
        return float(timeout)
    text = str(timeout).strip().lower()
    if text.endswith("s"):
        return float(text[:-1])
    if text.endswith("ms"):
        return float(text[:-2]) / 1000.0
    return float(text)


class APICheck:
    """HTTP probe used both for Step 3 (stack auto-selection) and Step 5
    (post-install API health check)."""

    def probe(
        self,
        url: str,
        method: str = "GET",
        expect_status: int = 200,
        expect_json: Optional[dict] = None,
        timeout: str | int | float = "30s",
        retries: int = 3,
        headers: Optional[dict] = None,
    ) -> CheckResult:
        timeout_s = _parse_timeout(timeout)
        last_error: Optional[str] = None

        for attempt in range(1, max(retries, 1) + 1):
            start = time.monotonic()
            try:
                response = httpx.request(method, url, timeout=timeout_s, headers=headers)
                elapsed_ms = (time.monotonic() - start) * 1000

                if response.status_code != expect_status:
                    last_error = (
                        f"Expected status {expect_status}, got {response.status_code}"
                    )
                else:
                    body: dict[str, Any] = {}
                    try:
                        body = response.json()
                    except Exception:
                        body = {}

                    if expect_json:
                        mismatches = [
                            f"{k}={v!r} (expected {expected!r})"
                            for k, expected in expect_json.items()
                            if (v := body.get(k)) != expected
                        ]
                        if mismatches:
                            last_error = f"JSON mismatch: {', '.join(mismatches)}"
                        else:
                            return CheckResult(
                                name="api_check",
                                status="pass",
                                detail=f"{response.status_code} OK",
                                response_time_ms=elapsed_ms,
                                raw=body,
                            )
                    else:
                        return CheckResult(
                            name="api_check",
                            status="pass",
                            detail=f"{response.status_code} OK",
                            response_time_ms=elapsed_ms,
                            raw=body,
                        )
            except httpx.HTTPError as exc:
                last_error = str(exc)

            if attempt < retries:
                time.sleep(min(0.5 * attempt, 2.0))

        return CheckResult(
            name="api_check",
            status="fail",
            detail=last_error or "Unknown error",
        )


def probe_project_stack(url: str, timeout: str | int | float = "10s") -> dict[str, Any]:
    """
    Probe a project's health/info endpoint and parse a stack descriptor
    out of the JSON response, used for Step 3 auto-selection.

    Expected (flexible) response shape, e.g.:
        {
          "framework": "laravel",
          "runtime": "php",
          "version": "8.2",
          "frontend": "react"
        }

    Returns a dict with keys: framework, runtime, version, frontend (any may be None),
    plus "raw" holding the full parsed response and "reachable" bool.
    """
    timeout_s = _parse_timeout(timeout)
    result: dict[str, Any] = {
        "reachable": False,
        "framework": None,
        "runtime": None,
        "version": None,
        "frontend": None,
        "raw": {},
    }
    try:
        response = httpx.get(url, timeout=timeout_s)
        result["reachable"] = response.status_code < 500
        body = response.json()
        if isinstance(body, dict):
            result["raw"] = body
            result["framework"] = body.get("framework")
            result["runtime"] = body.get("runtime")
            result["version"] = body.get("version")
            result["frontend"] = body.get("frontend")
    except Exception:
        pass
    return result
