from __future__ import annotations

from installer.stacks.db.base import BaseDBLayer


class MongoDBLayer(BaseDBLayer):
    """MongoDB 7.x local-install database layer."""

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
        # Add MongoDB GPG key and repo for Ubuntu
        self.adapter.run(
            "curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc "
            "| gpg --dearmor -o /usr/share/keyrings/mongodb-server-7.0.gpg"
        )
        self.adapter.run(
            "echo 'deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] "
            "https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse' "
            "> /etc/apt/sources.list.d/mongodb-org-7.0.list"
        )
        self.adapter.install_packages(["mongodb-org"])
        self.adapter.enable_service("mongod")
        self.adapter.start_service("mongod")
        self.adapter.run(
            f"mongosh --eval \""
            f"use {self.db_name}; "
            f"db.createUser({{user: '{self.db_user}', pwd: '{self.db_pass}', "
            f"roles: [{{role: 'readWrite', db: '{self.db_name}'}}]}})\" || true"
        )

    def connect_external(self) -> None:
        self.adapter.install_packages(["mongosh"])
        if not self.test_connection():
            raise RuntimeError("Cannot connect to external MongoDB — check credentials")

    def test_connection(self) -> bool:
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 27017)
        try:
            out = self.adapter.run(
                f"mongosh --host {host} --port {port} --eval 'db.runCommand({{ping:1}})' --quiet 2>&1"
                f" || mongo --host {host} --port {port} --eval 'db.runCommand({{ping:1}})' --quiet 2>&1"
            )
            return "ok" in out.lower()
        except Exception:
            return False

    def restore_backup(self, source: str) -> None:
        if source.startswith("http"):
            self.adapter.run(f"curl -fsSL {source} -o /tmp/mongo_backup.gz")
            self.adapter.run(f"mongorestore --gzip --archive=/tmp/mongo_backup.gz --db {self.db_name}")
        else:
            self.adapter.run(f"mongorestore --gzip --archive={source} --db {self.db_name}")

    def write_env(self, env_path: str) -> None:
        host = self.config.get("host", "localhost")
        port = self.config.get("port", 27017)
        uri = f"mongodb://{self.db_user}:{self.db_pass}@{host}:{port}/{self.db_name}"
        content = f"MONGODB_URI={uri}\nMONGODB_DB={self.db_name}\n"
        self.adapter.write_file(env_path, content)
