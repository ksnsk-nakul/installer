from __future__ import annotations

from installer.stacks.db.base import BaseDBLayer


class MySQLLayer(BaseDBLayer):
    """MySQL 8.x local-install database layer."""

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
        self.adapter.install_packages(["mysql-server"])
        self.adapter.enable_service("mysql")
        self.adapter.start_service("mysql")
        self.adapter.run(
            f"mysql -u root -e \""
            f"CREATE DATABASE IF NOT EXISTS {self.db_name}; "
            f"CREATE USER IF NOT EXISTS '{self.db_user}'@'localhost' IDENTIFIED BY '{self.db_pass}'; "
            f"GRANT ALL PRIVILEGES ON {self.db_name}.* TO '{self.db_user}'@'localhost'; "
            f"FLUSH PRIVILEGES;\""
        )

    def connect_external(self) -> None:
        self.adapter.install_packages(["mysql-client"])
        if not self.test_connection():
            raise RuntimeError("Cannot connect to external MySQL — check credentials")

    def test_connection(self) -> bool:
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 3306)
        user = self.config.get("user", "root")
        try:
            out = self.adapter.run(
                f"mysqladmin -h {host} -P {port} -u {user} ping 2>&1"
            )
            return "alive" in out.lower()
        except Exception:
            return False

    def restore_backup(self, source: str) -> None:
        if source.startswith("http"):
            self.adapter.run(f"curl -fsSL {source} | mysql -u {self.db_user} {self.db_name}")
        else:
            self.adapter.run(f"mysql -u {self.db_user} {self.db_name} < {source}")

    def write_env(self, env_path: str) -> None:
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 3306)
        content = (
            f"DB_CONNECTION=mysql\n"
            f"DB_HOST={host}\n"
            f"DB_PORT={port}\n"
            f"DB_DATABASE={self.db_name}\n"
            f"DB_USERNAME={self.db_user}\n"
            f"DB_PASSWORD={self.db_pass}\n"
        )
        self.adapter.write_file(env_path, content)
