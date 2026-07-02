from __future__ import annotations

from installer.stacks.frontend.base import BaseFrontend


class ReactFrontend(BaseFrontend):
    """React SPA — built with Vite (or npm run build), served via nginx."""

    def _run(self, cmd: str) -> str:
        return self.adapter.run(cmd)

    def build(self, project_path: str) -> None:
        output_dir = self.config.get("output_dir", "dist")
        self._run(f"cd {project_path} && npm install")
        self._run(f"cd {project_path} && npm run build")
        # Ensure output_dir exists after build
        self._run(f"test -d {project_path}/{output_dir} || (echo 'Build output not found'; exit 1)")

    def serve(self) -> None:
        domain = self.config.get("_domain", "localhost")
        project_path = self.config.get("_project_path", "/var/www/app")
        output_dir = self.config.get("output_dir", "dist")

        nginx_conf = f"""server {{
    listen 80;
    server_name {domain};
    root {project_path}/{output_dir};
    index index.html;

    location / {{
        try_files $uri $uri/ /index.html;
    }}
}}
"""
        self.adapter.write_file(f"/etc/nginx/sites-available/{domain}-spa", nginx_conf)
        self._run(f"ln -sf /etc/nginx/sites-available/{domain}-spa /etc/nginx/sites-enabled/{domain}-spa || true")
        self.adapter.enable_service("nginx")
        self.adapter.start_service("nginx")
