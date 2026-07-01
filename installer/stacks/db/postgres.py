from __future__ import annotations

from installer.stacks.db.base import BaseDBLayer


class PostgresLayer(BaseDBLayer):
    """PostgreSQL local-install database layer. Implementation lands in a later task."""

    def install_local(self) -> None:
        raise NotImplementedError

    def connect_external(self) -> None:
        raise NotImplementedError

    def test_connection(self) -> bool:
        raise NotImplementedError

    def restore_backup(self, source: str) -> None:
        raise NotImplementedError

    def write_env(self, env_path: str) -> None:
        raise NotImplementedError
