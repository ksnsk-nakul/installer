from __future__ import annotations

from installer.stacks.backend.base import BaseBackend


class LaravelBackend(BaseBackend):
    """Laravel (PHP 8.x) backend installer.

    Installs PHP + Composer, deploys the app, configures nginx + php-fpm,
    and optionally starts Queue worker and Scheduler via systemd.
    """

    # ── helpers ──────────────────────────────────────────────────────────────

    @property
    def php_version(self) -> str:
        return self.config.get("php_version") or "8.2"

    @property
    def with_queue(self) -> bool:
        return bool(self.config.get("queue", False))

    @property
    def with_scheduler(self) -> bool:
        return bool(self.config.get("scheduler", False))

    def _run(self, cmd: str) -> str:
        return self.adapter.run(cmd)

    # ── interface ─────────────────────────────────────────────────────────────

    def preflight(self) -> None:
        """Verify that the adapter can reach the target."""
        self._run("uname -s")

    def install(self) -> None:
        """Install PHP, required extensions, Composer, and nginx."""
        php = self.php_version

        # ondrej/php PPA for Ubuntu
        self._run("DEBIAN_FRONTEND=noninteractive apt-get update -y")
        self._run("DEBIAN_FRONTEND=noninteractive apt-get install -y software-properties-common curl")
        self._run("add-apt-repository -y ppa:ondrej/php || true")
        self._run("DEBIAN_FRONTEND=noninteractive apt-get update -y")

        extensions = [
            f"php{php}", f"php{php}-fpm", f"php{php}-cli",
            f"php{php}-mbstring", f"php{php}-xml", f"php{php}-zip",
            f"php{php}-curl", f"php{php}-bcmath", f"php{php}-tokenizer",
            f"php{php}-mysql", f"php{php}-pgsql",
            "nginx", "unzip", "git",
        ]
        self.adapter.install_packages(extensions)

        # Composer
        self._run(
            "curl -fsSL https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer"
        )

        # open web ports
        self.adapter.open_port(80, "tcp")
        self.adapter.open_port(443, "tcp")

    def configure(self) -> None:
        """Write nginx + php-fpm site config and .env."""
        php = self.php_version
        project_path = self.config.get("_project_path", "/var/www/app")
        domain = self.config.get("_domain", "localhost")

        nginx_conf = f"""server {{
    listen 80;
    server_name {domain};
    root {project_path}/public;
    index index.php;

    location / {{
        try_files $uri $uri/ /index.php?$query_string;
    }}

    location ~ \\.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php{php}-fpm.sock;
    }}

    location ~ /\\.ht {{
        deny all;
    }}
}}
"""
        self.adapter.write_file(f"/etc/nginx/sites-available/{domain}", nginx_conf)
        self._run(f"ln -sf /etc/nginx/sites-available/{domain} /etc/nginx/sites-enabled/{domain} || true")
        self._run("rm -f /etc/nginx/sites-enabled/default || true")
        self._run("nginx -t")

        if self.with_queue:
            queue_worker_conf = f"""[Unit]
Description=Laravel Queue Worker
After=network.target

[Service]
User=www-data
WorkingDirectory={project_path}
ExecStart=/usr/bin/php artisan queue:work --sleep=3 --tries=3
Restart=on-failure

[Install]
WantedBy=multi-user.target
"""
            self.adapter.write_file("/etc/systemd/system/laravel-queue.service", queue_worker_conf)

        if self.with_scheduler:
            cron_line = f"* * * * * www-data cd {project_path} && php artisan schedule:run >> /dev/null 2>&1"
            self.adapter.write_file("/etc/cron.d/laravel-scheduler", cron_line + "\n")

    def deploy(self, path: str) -> None:
        """Install Composer dependencies and run artisan commands."""
        self._run(f"cd {path} && composer install --no-dev --optimize-autoloader --no-interaction")
        self._run(f"cd {path} && php artisan key:generate --force")
        self._run(f"cd {path} && php artisan config:cache")
        self._run(f"cd {path} && php artisan route:cache")
        self._run(f"cd {path} && php artisan view:cache")
        self._run(f"cd {path} && php artisan migrate --force")
        self._run(f"chown -R www-data:www-data {path}")
        self._run(f"chmod -R 755 {path}/storage {path}/bootstrap/cache || true")

    def start(self) -> None:
        """Start and enable nginx, php-fpm, and optionally the queue worker."""
        php = self.php_version
        self.adapter.enable_service(f"php{php}-fpm")
        self.adapter.start_service(f"php{php}-fpm")
        self.adapter.enable_service("nginx")
        self.adapter.start_service("nginx")

        if self.with_queue:
            self._run("systemctl daemon-reload")
            self.adapter.enable_service("laravel-queue")
            self.adapter.start_service("laravel-queue")
