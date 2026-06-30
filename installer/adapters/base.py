from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    """Common interface implemented by Ubuntu, Docker, and Windows adapters.

    Stack layers (database/backend/frontend) depend only on this interface,
    never on the underlying transport (SSH/Docker SDK/WinRM).
    """

    @abstractmethod
    def detect(self) -> bool:
        """Return True if this adapter matches the target environment."""

    @abstractmethod
    def install_packages(self, packages: list[str]) -> None:
        """Install one or more system packages."""

    @abstractmethod
    def start_service(self, name: str) -> None:
        """Start a service/process by name."""

    @abstractmethod
    def enable_service(self, name: str) -> None:
        """Enable a service to start on boot."""

    @abstractmethod
    def open_port(self, port: int, protocol: str = "tcp") -> None:
        """Open a firewall port."""

    @abstractmethod
    def write_file(self, path: str, content: str) -> None:
        """Write content to a file on the target."""

    @abstractmethod
    def run(self, command: str) -> str:
        """Run a raw command on the target and return stdout."""

    @abstractmethod
    def get_info(self) -> dict[str, Any]:
        """Return environment metadata (OS name, version, etc.)."""
