from __future__ import annotations

from typing import Any

from installer.adapters.base import BaseAdapter
from installer.core.docker_client import DockerClientWrapper


class DockerAdapter(BaseAdapter):
    """Adapter for Docker environments using the Docker SDK.

    Unlike the Ubuntu/Windows adapters, "installing packages" inside a
    container is typically achieved by building/extending an image rather
    than running apt directly against a live container — but we still
    support direct package install for dev/debug containers.
    """

    def __init__(self, client: DockerClientWrapper) -> None:
        self.client = client

    def detect(self) -> bool:
        try:
            self.client.connect()
            return True
        except Exception:
            return False

    def install_packages(self, packages: list[str]) -> None:
        if not packages:
            return
        pkg_list = " ".join(packages)
        self.client.run(
            f"(apt-get update -y && apt-get install -y {pkg_list}) "
            f"|| (apk add --no-cache {pkg_list})"
        )

    def start_service(self, name: str) -> None:
        # Containers are typically single-process; "starting a service"
        # means launching it in the background inside the container.
        self.client.run(f"({name} &) || service {name} start")

    def enable_service(self, name: str) -> None:
        # No init system concept inside most containers — no-op by design.
        pass

    def open_port(self, port: int, protocol: str = "tcp") -> None:
        # Port exposure is handled at container-create / compose time,
        # not via a runtime firewall command. No-op here.
        pass

    def write_file(self, path: str, content: str) -> None:
        self.client.write_file(path, content)

    def run(self, command: str) -> str:
        return self.client.run(command)

    def get_info(self) -> dict[str, Any]:
        return self.client.info()

    def generate_dockerfile(self, base_image: str, commands: list[str]) -> str:
        """Generate a Dockerfile string from a base image and RUN commands."""
        lines = [f"FROM {base_image}"]
        for cmd in commands:
            lines.append(f"RUN {cmd}")
        return "\n".join(lines) + "\n"

    def build_image(self, path: str, tag: str, dockerfile: str = "Dockerfile") -> str:
        return self.client.build_image(path, tag, dockerfile)
