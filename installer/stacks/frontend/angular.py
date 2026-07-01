from __future__ import annotations

from installer.stacks.frontend.base import BaseFrontend


class AngularFrontend(BaseFrontend):
    """Angular SPA, built and served via nginx. Full implementation lands in a later task."""

    def build(self, project_path: str) -> None:
        raise NotImplementedError

    def serve(self) -> None:
        raise NotImplementedError
