from __future__ import annotations

from installer.stacks.frontend.base import BaseFrontend

# SSR frameworks handled here: Next.js, Nuxt, Blade (Laravel-managed), Jinja2 (Django-managed)
# Blade and Jinja2 are rendered by the backend process — build() is a no-op for those.
_BACKEND_RENDERED = {"blade", "jinja2"}


class SSRFrontend(BaseFrontend):
    """Server-rendered frontend: Blade, Jinja2, Next.js, Nuxt."""

    @property
    def framework(self) -> str:
        return self.config.get("framework") or "next"

    def _run(self, cmd: str) -> str:
        return self.adapter.run(cmd)

    def build(self, project_path: str) -> None:
        if self.framework in _BACKEND_RENDERED:
            # Backend process handles rendering — nothing to build separately
            return
        # Next.js / Nuxt
        self._run(f"cd {project_path} && npm install")
        self._run(f"cd {project_path} && npm run build")

    def serve(self) -> None:
        if self.framework in _BACKEND_RENDERED:
            # nginx is configured by the backend (Laravel/Django) — nothing to do
            return

        domain = self.config.get("_domain", "localhost")
        project_path = self.config.get("_project_path", "/var/www/app")
        app_port = self.config.get("_app_port", 3000)

        # Next.js / Nuxt are Node SSR servers — proxy via nginx, start with PM2
        nginx_conf = f"""server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://127.0.0.1:{app_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
}}
"""
        self.adapter.write_file(f"/etc/nginx/sites-available/{domain}-ssr", nginx_conf)
        self._run(f"ln -sf /etc/nginx/sites-available/{domain}-ssr /etc/nginx/sites-enabled/{domain}-ssr || true")

        app_name = f"{self.framework}-ssr"
        self._run(f"cd {project_path} && pm2 start npm --name {app_name} -- start")
        self._run("pm2 save")
        self.adapter.enable_service("nginx")
        self.adapter.start_service("nginx")
