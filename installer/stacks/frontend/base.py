from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from installer.adapters.base import BaseAdapter


class BaseFrontend(ABC):
    """Common interface for all frontend framework implementations."""

    def __init__(self, adapter: BaseAdapter, config: dict[str, Any]) -> None:
        self.adapter = adapter
        self.config = config

    @abstractmethod
    def build(self, project_path: str) -> None:
        """Install deps and build the frontend (SPA) or compile assets (SSR)."""

    @abstractmethod
    def serve(self) -> None:
        """Configure the web server (nginx/IIS) to serve the built output."""

    def run_all(self, project_path: str) -> None:
        """Convenience entrypoint used by the engine."""
        self.build(project_path)
        self.serve()


class NoneFrontend(BaseFrontend):
    """Used when frontend is API-only and the frontend step is skipped."""

    def build(self, project_path: str) -> None:
        pass

    def serve(self) -> None:
        pass
