from __future__ import annotations

from installer.stacks.db.base import BaseDBLayer


class ExternalDBLayer(BaseDBLayer):
    """Connects to an external DB provider (Supabase, PlanetScale, Atlas, RDS, Neon).

    Validates connectivity and writes .env credentials — does not install a local DB server.
    """

    def install_local(self) -> None:
        raise NotImplementedError("External DB layer has no local install step")

    def connect_external(self) -> None:
        engine = self.config.get("engine", "postgresql")
        host = self.config.get("host")
        if not host:
            raise ValueError("External DB mode requires 'host' in database config")
        # Install the appropriate client to validate connectivity
        if engine in ("mysql",):
            self.adapter.install_packages(["mysql-client"])
        elif engine in ("postgresql",):
            self.adapter.install_packages(["postgresql-client"])
        elif engine in ("mongodb",):
            self.adapter.install_packages(["mongosh"])
        if not self.test_connection():
            raise RuntimeError(
                f"Cannot connect to external {engine} at {host} — check credentials and network"
            )

    def test_connection(self) -> bool:
        engine = self.config.get("engine", "postgresql")
        host = self.config.get("host", "localhost")
        port = self.config.get("port")
        user = self.config.get("user", "root")
        try:
            if engine == "mysql":
                port = port or 3306
                out = self.adapter.run(f"mysqladmin -h {host} -P {port} -u {user} ping 2>&1")
                return "alive" in out.lower()
            elif engine == "postgresql":
                port = port or 5432
                out = self.adapter.run(f"pg_isready -h {host} -p {port} -U {user} 2>&1")
                return "accepting connections" in out.lower()
            elif engine == "mongodb":
                port = port or 27017
                out = self.adapter.run(
                    f"mongosh --host {host} --port {port} --eval 'db.runCommand({{ping:1}})' --quiet 2>&1"
                )
                return "ok" in out.lower()
        except Exception:
            pass
        return False

    def restore_backup(self, source: str) -> None:
        engine = self.config.get("engine", "postgresql")
        db_name = self.config.get("db_name", "app_db")
        user = self.config.get("user", "root")
        if engine == "mysql":
            if source.startswith("http"):
                self.adapter.run(f"curl -fsSL {source} | mysql -u {user} {db_name}")
            else:
                self.adapter.run(f"mysql -u {user} {db_name} < {source}")
        elif engine == "postgresql":
            if source.startswith("http"):
                self.adapter.run(f"curl -fsSL {source} | psql -U {user} {db_name}")
            else:
                self.adapter.run(f"psql -U {user} {db_name} < {source}")

    def write_env(self, env_path: str) -> None:
        engine = self.config.get("engine", "postgresql")
        host = self.config.get("host", "localhost")
        port = self.config.get("port", "")
        db_name = self.config.get("db_name", "app_db")
        user = self.config.get("user", "root")
        password = self.config.get("password", "")

        if engine == "mysql":
            content = (
                f"DB_CONNECTION=mysql\nDB_HOST={host}\nDB_PORT={port or 3306}\n"
                f"DB_DATABASE={db_name}\nDB_USERNAME={user}\nDB_PASSWORD={password}\n"
            )
        elif engine == "postgresql":
            content = (
                f"DB_CONNECTION=pgsql\nDB_HOST={host}\nDB_PORT={port or 5432}\n"
                f"DB_DATABASE={db_name}\nDB_USERNAME={user}\nDB_PASSWORD={password}\n"
            )
        elif engine == "mongodb":
            content = (
                f"MONGODB_URI=mongodb://{user}:{password}@{host}:{port or 27017}/{db_name}\n"
            )
        else:
            content = f"DATABASE_URL={engine}://{user}:{password}@{host}/{db_name}\n"

        self.adapter.write_file(env_path, content)
