from __future__ import annotations

from typing import Any

from installer.adapters.base import BaseAdapter
from installer.core.detector import Environment, detect_environment


class WindowsAdapter(BaseAdapter):
    """Adapter for Windows servers reached over WinRM, using Chocolatey/PowerShell/IIS."""

    def __init__(self, runner: Any) -> None:
        """runner satisfies the CommandRunner protocol (e.g. WinRMClient)."""
        self.runner = runner
        self._info: dict | None = None

    def detect(self) -> bool:
        env, info = detect_environment(self.runner)
        self._info = info
        return env == Environment.WINDOWS

    def install_packages(self, packages: list[str]) -> None:
        if not packages:
            return
        for pkg in packages:
            self.runner.run(f"choco install {pkg} -y")

    def start_service(self, name: str) -> None:
        self.runner.run(f"Start-Service -Name '{name}'")

    def enable_service(self, name: str) -> None:
        self.runner.run(f"Set-Service -Name '{name}' -StartupType Automatic")

    def open_port(self, port: int, protocol: str = "tcp") -> None:
        proto = protocol.upper()
        self.runner.run(
            f"New-NetFirewallRule -DisplayName 'installer-port-{port}' "
            f"-Direction Inbound -Protocol {proto} -LocalPort {port} -Action Allow"
        )

    def write_file(self, path: str, content: str) -> None:
        self.runner.write_file(path, content)

    def run(self, command: str) -> str:
        return self.runner.run(command)

    def get_info(self) -> dict[str, Any]:
        if self._info is None:
            self.detect()
        return self._info or {}
