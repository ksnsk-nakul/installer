from __future__ import annotations

from installer.stacks.backend.base import BaseBackend


class JavaBackend(BaseBackend):
    """Spring Boot (Java) backend. Full implementation lands in a later task."""

    def preflight(self) -> None:
        raise NotImplementedError

    def install(self) -> None:
        raise NotImplementedError

    def configure(self) -> None:
        raise NotImplementedError

    def deploy(self, path: str) -> None:
        raise NotImplementedError

    def start(self) -> None:
        raise NotImplementedError
