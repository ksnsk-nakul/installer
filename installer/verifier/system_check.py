from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from installer.verifier.api_check import APICheck, CheckResult


@dataclass
class SystemCheckResult:
    name: str
    status: str  # "pass" | "warn" | "fail"
    detail: str = ""
    fix_hint: Optional[str] = None


class SystemCheck:
    """Post-install system verifier (Step 5).

    Each check method accepts a CommandRunner (adapter.run) and returns a
    SystemCheckResult. The run() method executes all enabled checks and
    returns a summary.
    """

    def check_service(self, runner: Any, service_name: str) -> SystemCheckResult:
        """Verify a systemd/init service is active."""
        try:
            out = runner.run(f"systemctl is-active {service_name} 2>/dev/null || service {service_name} status 2>/dev/null | head -1")
            low = out.lower()
            if re.search(r"\bactive\b", low) or "running" in low:
                return SystemCheckResult(name=f"service:{service_name}", status="pass", detail=out.strip())
            return SystemCheckResult(
                name=f"service:{service_name}",
                status="fail",
                detail=out.strip(),
                fix_hint=f"systemctl start {service_name}",
            )
        except Exception as exc:
            return SystemCheckResult(
                name=f"service:{service_name}",
                status="fail",
                detail=str(exc),
                fix_hint=f"systemctl start {service_name}",
            )

    def check_port(self, runner: Any, port: int) -> SystemCheckResult:
        """Verify a TCP port is listening."""
        try:
            out = runner.run(f"ss -tlnp 2>/dev/null | grep ':{port} ' || netstat -tlnp 2>/dev/null | grep ':{port} '")
            if out.strip():
                return SystemCheckResult(name=f"port:{port}", status="pass", detail=f"Port {port} is open")
            return SystemCheckResult(
                name=f"port:{port}",
                status="fail",
                detail=f"Port {port} is not listening",
                fix_hint=f"Check service bound to port {port}",
            )
        except Exception as exc:
            return SystemCheckResult(
                name=f"port:{port}",
                status="fail",
                detail=str(exc),
                fix_hint=f"Check service bound to port {port}",
            )

    def check_ssl(self, runner: Any, domain: str) -> SystemCheckResult:
        """Check SSL certificate expiry via openssl."""
        try:
            out = runner.run(
                f"echo | openssl s_client -connect {domain}:443 -servername {domain} 2>/dev/null "
                f"| openssl x509 -noout -dates 2>/dev/null"
            )
            m = re.search(r"notAfter=(.*)", out)
            if m:
                return SystemCheckResult(
                    name=f"ssl:{domain}",
                    status="pass",
                    detail=f"SSL cert valid until: {m.group(1).strip()}",
                )
            return SystemCheckResult(
                name=f"ssl:{domain}",
                status="warn",
                detail="Could not parse SSL certificate expiry",
            )
        except Exception as exc:
            return SystemCheckResult(
                name=f"ssl:{domain}",
                status="warn",
                detail=str(exc),
                fix_hint=f"certbot renew for {domain}",
            )

    def check_db_connectivity(self, runner: Any, engine: str, db_config: dict) -> SystemCheckResult:
        """Ping the database to verify connectivity."""
        host = db_config.get("host", "localhost")
        port = db_config.get("port")
        user = db_config.get("user", "root")

        try:
            if engine in ("mysql",):
                port = port or 3306
                out = runner.run(f"mysqladmin -h {host} -P {port} -u {user} ping 2>&1")
                if "alive" in out.lower():
                    return SystemCheckResult(name=f"db:{engine}", status="pass", detail="MySQL is alive")
            elif engine in ("postgresql",):
                port = port or 5432
                out = runner.run(f"pg_isready -h {host} -p {port} -U {user} 2>&1")
                if "accepting connections" in out.lower():
                    return SystemCheckResult(name=f"db:{engine}", status="pass", detail="PostgreSQL is ready")
            elif engine in ("mongodb",):
                port = port or 27017
                out = runner.run(
                    f"mongosh --host {host} --port {port} --eval 'db.runCommand({{ping:1}})' --quiet 2>&1"
                    f" || mongo --host {host} --port {port} --eval 'db.runCommand({{ping:1}})' --quiet 2>&1"
                )
                if "ok" in out.lower():
                    return SystemCheckResult(name=f"db:{engine}", status="pass", detail="MongoDB is reachable")

            return SystemCheckResult(
                name=f"db:{engine}",
                status="fail",
                detail=f"DB ping did not confirm connectivity",
                fix_hint=f"Check {engine} service is running and credentials are correct",
            )
        except Exception as exc:
            return SystemCheckResult(
                name=f"db:{engine}",
                status="fail",
                detail=str(exc),
                fix_hint=f"Check {engine} service and credentials",
            )

    def run(
        self,
        runner: Any,
        services: list[str] | None = None,
        ports: list[int] | None = None,
        domain: str | None = None,
        db_engine: str | None = None,
        db_config: dict | None = None,
        api_check_config: dict | None = None,
    ) -> list[SystemCheckResult]:
        """Execute all configured checks and return results."""
        results: list[SystemCheckResult] = []

        for svc in services or []:
            results.append(self.check_service(runner, svc))

        for port in ports or []:
            results.append(self.check_port(runner, port))

        if domain:
            results.append(self.check_ssl(runner, domain))

        if db_engine and db_config:
            results.append(self.check_db_connectivity(runner, db_engine, db_config))

        if api_check_config:
            api_result = APICheck().probe(**api_check_config)
            results.append(
                SystemCheckResult(
                    name="api_health",
                    status=api_result.status,
                    detail=api_result.detail,
                )
            )

        return results

    @staticmethod
    def summary(results: list[SystemCheckResult]) -> dict[str, int]:
        counts: dict[str, int] = {"pass": 0, "warn": 0, "fail": 0}
        for r in results:
            counts[r.status] = counts.get(r.status, 0) + 1
        return counts
