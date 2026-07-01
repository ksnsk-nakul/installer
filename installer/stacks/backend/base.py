from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from installer.adapters.base import BaseAdapter


class BaseBackend(ABC):
    """Common interface for all backend framework implementations."""

    def __init__(self, adapter: BaseAdapter, config: dict[str, Any]) -> None:
        self.adapter = adapter
        self.config = config

    @abstractmethod
    def preflight(self) -> None:
        """Check prerequisites (runtime versions, required binaries, etc.)."""

    @abstractmethod
    def install(self) -> None:
        """Install runtime + packages."""

    @abstractmethod
    def configure(self) -> None:
        """Write config files, .env, etc."""

    @abstractmethod
    def deploy(self, path: str) -> None:
        """Deploy app code to the target."""

    @abstractmethod
    def start(self) -> None:
        """Start the service / process manager."""

    def run_all(self, project_path: str) -> None:
        """Convenience entrypoint used by the engine."""
        self.preflight()
        self.install()
        self.configure()
        self.deploy(project_path)
        self.start()
