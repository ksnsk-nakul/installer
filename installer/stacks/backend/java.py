from __future__ import annotations

from installer.stacks.backend.base import BaseBackend


class JavaBackend(BaseBackend):
    """Spring Boot (Java 17/21) backend — builds JAR via Maven/Gradle, serves via systemd + nginx."""

    @property
    def java_version(self) -> str:
        return str(self.config.get("java_version") or "17")

    @property
    def build_tool(self) -> str:
        return self.config.get("build_tool") or "maven"

    def _run(self, cmd: str) -> str:
        return self.adapter.run(cmd)

    def preflight(self) -> None:
        self._run("uname -s")

    def install(self) -> None:
        jv = self.java_version
        self._run("DEBIAN_FRONTEND=noninteractive apt-get update -y")
        packages = [f"openjdk-{jv}-jdk", "nginx"]
        if self.build_tool == "maven":
            packages.append("maven")
        else:
            # Gradle installed via wrapper in the project; no system package needed
            pass
        self.adapter.install_packages(packages)
        self.adapter.open_port(80, "tcp")
        self.adapter.open_port(443, "tcp")

    def configure(self) -> None:
        domain = self.config.get("_domain", "localhost")
        app_port = self.config.get("_app_port", 8080)
        project_path = self.config.get("_project_path", "/var/www/app")

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
        self.adapter.write_file(f"/etc/nginx/sites-available/{domain}", nginx_conf)
        self._run(f"ln -sf /etc/nginx/sites-available/{domain} /etc/nginx/sites-enabled/{domain} || true")
        self._run("rm -f /etc/nginx/sites-enabled/default || true")
        self._run("nginx -t")

        springboot_service = f"""[Unit]
Description=Spring Boot Application — {domain}
After=network.target

[Service]
User=www-data
WorkingDirectory={project_path}
ExecStart=/usr/bin/java -jar {project_path}/app.jar
Restart=on-failure
SuccessExitStatus=143

[Install]
WantedBy=multi-user.target
"""
        self.adapter.write_file("/etc/systemd/system/springboot.service", springboot_service)

    def deploy(self, path: str) -> None:
        if self.build_tool == "maven":
            self._run(f"cd {path} && mvn package -DskipTests")
            # Rename artifact to app.jar for predictability
            self._run(f"find {path}/target -name '*.jar' ! -name '*sources*' | head -1 | xargs -I{{}} cp {{}} {path}/app.jar")
        else:
            self._run(f"cd {path} && ./gradlew bootJar")
            self._run(f"find {path}/build/libs -name '*.jar' ! -name '*plain*' | head -1 | xargs -I{{}} cp {{}} {path}/app.jar")
        self._run(f"chown -R www-data:www-data {path}")

    def start(self) -> None:
        self._run("systemctl daemon-reload")
        self.adapter.enable_service("springboot")
        self.adapter.start_service("springboot")
        self.adapter.enable_service("nginx")
        self.adapter.start_service("nginx")
