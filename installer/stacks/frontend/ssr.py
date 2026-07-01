from __future__ import annotations

from installer.stacks.frontend.base import BaseFrontend


class SSRFrontend(BaseFrontend):
    """Server-rendered frontend: Blade, Jinja2, Next.js, Nuxt.

    Full implementation lands in a later task.
    """

    def build(self, project_path: str) -> None:
        raise NotImplementedError

    def serve(self) -> None:
        raise NotImplementedError
