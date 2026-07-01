from __future__ import annotations

from installer.stacks.db.base import BaseDBLayer


class ExternalDBLayer(BaseDBLayer):
    """Connects to an external DB provider (Supabase, PlanetScale, Atlas, RDS, Neon).

    Implementation lands in a later task.
    """

    def install_local(self) -> None:
        raise NotImplementedError("External DB layer has no local install step")

    def connect_external(self) -> None:
        raise NotImplementedError

    def test_connection(self) -> bool:
        raise NotImplementedError

    def restore_backup(self, source: str) -> None:
        raise NotImplementedError

    def write_env(self, env_path: str) -> None:
        raise NotImplementedError
