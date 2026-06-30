from __future__ import annotations

from pathlib import Path
from typing import Optional

import paramiko


class SSHError(RuntimeError):
    """Raised when an SSH command fails or the connection cannot be established."""


class SSHClient:
    """Thin wrapper around Paramiko satisfying the CommandRunner protocol."""

    def __init__(
        self,
        host: str,
        user: str = "root",
        key_path: Optional[str] = None,
        password: Optional[str] = None,
        port: int = 22,
        timeout: int = 15,
    ) -> None:
        self.host = host
        self.user = user
        self.key_path = key_path
        self.password = password
        self.port = port
        self.timeout = timeout
        self._client: Optional[paramiko.SSHClient] = None

    def connect(self) -> None:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_kwargs: dict = {
            "hostname": self.host,
            "port": self.port,
            "username": self.user,
            "timeout": self.timeout,
        }
        if self.key_path:
            connect_kwargs["key_filename"] = str(Path(self.key_path).expanduser())
        if self.password:
            connect_kwargs["password"] = self.password
        try:
            client.connect(**connect_kwargs)
        except Exception as exc:
            raise SSHError(f"Failed to connect to {self.host}: {exc}") from exc
        self._client = client

    def run(self, command: str) -> str:
        """Execute command and return stdout. Raise SSHError on non-zero exit."""
        if self._client is None:
            self.connect()
        assert self._client is not None
        stdin, stdout, stderr = self._client.exec_command(command, timeout=self.timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        if exit_code != 0:
            raise SSHError(f"Command failed (exit {exit_code}): {command}\n{err}")
        return out

    def write_file(self, path: str, content: str) -> None:
        if self._client is None:
            self.connect()
        assert self._client is not None
        sftp = self._client.open_sftp()
        try:
            with sftp.file(path, "w") as f:
                f.write(content)
        finally:
            sftp.close()

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "SSHClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
