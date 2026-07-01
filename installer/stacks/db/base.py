from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from installer.adapters.base import BaseAdapter


class BaseDBLayer(ABC):
    """Common interface for all database layer implementations."""

    def __init__(self, adapter: BaseAdapter, config: dict[str, Any]) -> None:
        self.adapter = adapter
        self.config = config

    @abstractmethod
    def install_local(self) -> None:
        """Install and configure the DB server locally (mode == 'local')."""

    @abstractmethod
    def connect_external(self) -> None:
        """Validate connectivity to an external provider (mode == 'external')."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Return True if the configured database is reachable."""

    @abstractmethod
    def restore_backup(self, source: str) -> None:
        """Restore a backup file/URL into the database."""

    @abstractmethod
    def write_env(self, env_path: str) -> None:
        """Write DB connection variables to the target .env file."""

    def setup(self) -> None:
        """Convenience entrypoint used by the engine: dispatches to local/external."""
        if self.config.get("mode") == "external":
            self.connect_external()
        else:
            self.install_local()
        backup = self.config.get("backup_url") or self.config.get("backup_file")
        if backup:
            self.restore_backup(backup)
