from __future__ import annotations

from typing import Optional

import docker
from docker.errors import APIError, DockerException


class DockerClientError(RuntimeError):
    """Raised when a Docker operation fails."""


class DockerClientWrapper:
    """Thin wrapper around the Docker SDK satisfying the CommandRunner protocol.

    `run()` executes a command inside a running container (or, if no container
    is configured, against the daemon host via `docker run --rm`-style exec).
    """

    def __init__(self, container_name: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self.container_name = container_name
        self.base_url = base_url
        self._client: Optional[docker.DockerClient] = None

    def connect(self) -> None:
        try:
            self._client = (
                docker.DockerClient(base_url=self.base_url)
                if self.base_url
                else docker.from_env()
            )
            self._client.ping()
        except DockerException as exc:
            raise DockerClientError(f"Failed to connect to Docker daemon: {exc}") from exc

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            self.connect()
        assert self._client is not None
        return self._client

    def run(self, command: str) -> str:
        """Execute command inside the configured container and return stdout."""
        if not self.container_name:
            raise DockerClientError("No container_name configured for exec")
        try:
            container = self.client.containers.get(self.container_name)
            exit_code, output = container.exec_run(["sh", "-c", command])
            text = output.decode("utf-8", errors="replace") if isinstance(output, bytes) else str(output)
            if exit_code != 0:
                raise DockerClientError(f"Command failed (exit {exit_code}): {command}\n{text}")
            return text
        except APIError as exc:
            raise DockerClientError(f"Docker exec failed: {exc}") from exc

    def build_image(self, path: str, tag: str, dockerfile: str = "Dockerfile") -> str:
        try:
            image, _logs = self.client.images.build(path=path, tag=tag, dockerfile=dockerfile)
            return image.id
        except (APIError, DockerException) as exc:
            raise DockerClientError(f"Image build failed: {exc}") from exc

    def write_file(self, path: str, content: str) -> None:
        """Write content to a file inside the configured container via base64 echo."""
        import base64

        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        self.run(f"echo {encoded} | base64 -d > {path}")

    def info(self) -> dict:
        try:
            return self.client.info()
        except DockerException as exc:
            raise DockerClientError(f"Failed to fetch Docker info: {exc}") from exc
