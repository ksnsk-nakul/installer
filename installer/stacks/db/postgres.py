from __future__ import annotations

from installer.stacks.db.base import BaseDBLayer


class PostgresLayer(BaseDBLayer):
    """PostgreSQL 15/16 local-install database layer."""

    @property
    def db_name(self) -> str:
        return self.config.get("db_name") or "app_db"

    @property
    def db_user(self) -> str:
        return self.config.get("user") or "app_user"

    @property
    def db_pass(self) -> str:
        return self.config.get("password") or "changeme"

    def install_local(self) -> None:
        self.adapter.install_packages(["postgresql", "postgresql-contrib"])
        self.adapter.enable_service("postgresql")
        self.adapter.start_service("postgresql")
        self.adapter.run(
            f"sudo -u postgres psql -c \""
            f"CREATE DATABASE {self.db_name}; "
            f"\" 2>/dev/null || true"
        )
        self.adapter.run(
            f"sudo -u postgres psql -c \""
            f"CREATE USER {self.db_user} WITH PASSWORD '{self.db_pass}'; "
            f"GRANT ALL PRIVILEGES ON DATABASE {self.db_name} TO {self.db_user}; "
            f"\""
        )

    def connect_external(self) -> None:
        self.adapter.install_packages(["postgresql-client"])
        if not self.test_connection():
            raise RuntimeError("Cannot connect to external PostgreSQL — check credentials")

    def test_connection(self) -> bool:
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 5432)
        user = self.config.get("user", "postgres")
        try:
            out = self.adapter.run(
                f"pg_isready -h {host} -p {port} -U {user} 2>&1"
            )
            return "accepting connections" in out.lower()
        except Exception:
            return False

    def restore_backup(self, source: str) -> None:
        if source.startswith("http"):
            self.adapter.run(
                f"curl -fsSL {source} | psql -U {self.db_user} {self.db_name}"
            )
        else:
            self.adapter.run(f"psql -U {self.db_user} {self.db_name} < {source}")

    def write_env(self, env_path: str) -> None:
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 5432)
        content = (
            f"DB_CONNECTION=pgsql\n"
            f"DB_HOST={host}\n"
            f"DB_PORT={port}\n"
            f"DB_DATABASE={self.db_name}\n"
            f"DB_USERNAME={self.db_user}\n"
            f"DB_PASSWORD={self.db_pass}\n"
        )
        self.adapter.write_file(env_path, content)
