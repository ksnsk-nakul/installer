from __future__ import annotations

from typing import Any

from installer.adapters.base import BaseAdapter
from installer.core.detector import Environment, detect_environment


class UbuntuAdapter(BaseAdapter):
    """Adapter for Ubuntu/Debian servers reached over SSH, using apt/systemd/ufw."""

    def __init__(self, runner: Any) -> None:
        """runner satisfies the CommandRunner protocol (e.g. SSHClient)."""
        self.runner = runner
        self._info: dict | None = None

    def detect(self) -> bool:
        env, info = detect_environment(self.runner)
        self._info = info
        return env in (Environment.UBUNTU, Environment.DEBIAN)

    def install_packages(self, packages: list[str]) -> None:
        if not packages:
            return
        pkg_list = " ".join(packages)
        self.runner.run("DEBIAN_FRONTEND=noninteractive apt-get update -y")
        self.runner.run(f"DEBIAN_FRONTEND=noninteractive apt-get install -y {pkg_list}")

    def start_service(self, name: str) -> None:
        self.runner.run(f"systemctl start {name}")

    def enable_service(self, name: str) -> None:
        self.runner.run(f"systemctl enable {name}")

    def open_port(self, port: int, protocol: str = "tcp") -> None:
        self.runner.run(f"ufw allow {port}/{protocol}")

    def write_file(self, path: str, content: str) -> None:
        if hasattr(self.runner, "write_file"):
            self.runner.write_file(path, content)
            return
        import base64
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        self.runner.run(f"echo {encoded} | base64 -d > {path}")

    def run(self, command: str) -> str:
        return self.runner.run(command)

    def get_info(self) -> dict[str, Any]:
        if self._info is None:
            self.detect()
        return self._info or {}
