from __future__ import annotations

from installer.stacks.frontend.base import BaseFrontend


class ReactFrontend(BaseFrontend):
    """React SPA, built with Vite, served via nginx. Full implementation lands in a later task."""

    def build(self, project_path: str) -> None:
        raise NotImplementedError

    def serve(self) -> None:
        raise NotImplementedError
