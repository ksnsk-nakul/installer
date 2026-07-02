from __future__ import annotations

from installer.stacks.backend.base import BaseBackend

# Supports Django, FastAPI, and Flask — all served via gunicorn + nginx

_WSGI_FRAMEWORKS = {"django", "flask"}
_ASGI_FRAMEWORKS = {"fastapi"}


class PythonBackend(BaseBackend):
    """Django / FastAPI / Flask backend — installs Python 3.11+, venv, gunicorn, nginx."""

    @property
    def framework(self) -> str:
        return self.config.get("framework", "django")

    @property
    def python_version(self) -> str:
        return self.config.get("python_version") or "3.11"

    @property
    def is_asgi(self) -> bool:
        return self.framework in _ASGI_FRAMEWORKS

    def _run(self, cmd: str) -> str:
        return self.adapter.run(cmd)

    def preflight(self) -> None:
        self._run("uname -s")

    def install(self) -> None:
        py = self.python_version
        self._run("DEBIAN_FRONTEND=noninteractive apt-get update -y")
        packages = [f"python{py}", f"python{py}-venv", f"python{py}-dev",
                    "python3-pip", "nginx", "build-essential", "libpq-dev"]
        self.adapter.install_packages(packages)
        self.adapter.open_port(80, "tcp")
        self.adapter.open_port(443, "tcp")

    def configure(self) -> None:
        domain = self.config.get("_domain", "localhost")
        app_port = self.config.get("_app_port", 8000)
        project_path = self.config.get("_project_path", "/var/www/app")
        workers = self.config.get("_workers", 3)
        app_module = self.config.get("_wsgi_module", "app.wsgi:application")

        nginx_conf = f"""server {{
    listen 80;
    server_name {domain};

    location / {{
        proxy_pass http://127.0.0.1:{app_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}
}}
"""
        self.adapter.write_file(f"/etc/nginx/sites-available/{domain}", nginx_conf)
        self._run(f"ln -sf /etc/nginx/sites-available/{domain} /etc/nginx/sites-enabled/{domain} || true")
        self._run("rm -f /etc/nginx/sites-enabled/default || true")
        self._run("nginx -t")

        # systemd service for gunicorn
        worker_class = "uvicorn.workers.UvicornWorker" if self.is_asgi else "sync"
        gunicorn_service = f"""[Unit]
Description=Gunicorn daemon for {domain}
After=network.target

[Service]
User=www-data
WorkingDirectory={project_path}
ExecStart={project_path}/venv/bin/gunicorn \\
    --workers {workers} \\
    --worker-class {worker_class} \\
    --bind 127.0.0.1:{app_port} \\
    {app_module}
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""
        self.adapter.write_file("/etc/systemd/system/gunicorn.service", gunicorn_service)

    def deploy(self, path: str) -> None:
        py = self.python_version
        self._run(f"python{py} -m venv {path}/venv")
        self._run(f"{path}/venv/bin/pip install --upgrade pip")
        self._run(f"{path}/venv/bin/pip install gunicorn uvicorn")
        # Install project requirements
        self._run(
            f"[ -f {path}/requirements.txt ] && {path}/venv/bin/pip install -r {path}/requirements.txt || true"
        )
        if self.framework == "django":
            self._run(f"cd {path} && {path}/venv/bin/python manage.py collectstatic --noinput || true")
            self._run(f"cd {path} && {path}/venv/bin/python manage.py migrate --noinput || true")
        self._run(f"chown -R www-data:www-data {path}")

    def start(self) -> None:
        self._run("systemctl daemon-reload")
        self.adapter.enable_service("gunicorn")
        self.adapter.start_service("gunicorn")
        self.adapter.enable_service("nginx")
        self.adapter.start_service("nginx")
