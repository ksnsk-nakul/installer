from __future__ import annotations

from installer.stacks.backend.base import BaseBackend


class NodeBackend(BaseBackend):
    """Node.js / Express backend — installs Node LTS via nvm, serves via PM2 + nginx."""

    @property
    def node_version(self) -> str:
        return self.config.get("node_version") or "lts"

    def _run(self, cmd: str) -> str:
        return self.adapter.run(cmd)

    def preflight(self) -> None:
        self._run("uname -s")

    def install(self) -> None:
        # Install Node.js via NodeSource
        self._run("DEBIAN_FRONTEND=noninteractive apt-get update -y")
        self.adapter.install_packages(["curl", "nginx"])
        self._run(
            "curl -fsSL https://deb.nodesource.com/setup_lts.x | bash -"
        )
        self.adapter.install_packages(["nodejs"])
        # PM2 process manager
        self._run("npm install -g pm2")
        self.adapter.open_port(80, "tcp")
        self.adapter.open_port(443, "tcp")

    def configure(self) -> None:
        domain = self.config.get("_domain", "localhost")
        app_port = self.config.get("_app_port", 3000)
        project_path = self.config.get("_project_path", "/var/www/app")

        nginx_conf = f"""server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://127.0.0.1:{app_port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }}
}}
"""
        self.adapter.write_file(f"/etc/nginx/sites-available/{domain}", nginx_conf)
        self._run(f"ln -sf /etc/nginx/sites-available/{domain} /etc/nginx/sites-enabled/{domain} || true")
        self._run("rm -f /etc/nginx/sites-enabled/default || true")
        self._run("nginx -t")

    def deploy(self, path: str) -> None:
        self._run(f"cd {path} && npm install --production")
        # PM2 ecosystem file path convention
        self._run(f"cd {path} && pm2 delete all 2>/dev/null || true")

    def start(self) -> None:
        project_path = self.config.get("_project_path", "/var/www/app")
        app_entry = self.config.get("_entry", "server.js")
        app_name = self.config.get("_name", "app")
        self._run(f"cd {project_path} && pm2 start {app_entry} --name {app_name}")
        self._run("pm2 save")
        self._run("pm2 startup systemd -u root --hp /root || true")
        self.adapter.enable_service("nginx")
        self.adapter.start_service("nginx")
