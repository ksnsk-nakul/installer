# Installer / Verifier Tool — Design Spec
*Date: 2026-06-29*

## Overview

A Python-based CLI tool with a built-in web dashboard that transforms a bare server — Ubuntu, Docker, or Windows — into a fully configured, running web application. The web dashboard uses an app store–style UI (Explore / Installed / Verify / Updates / Clone) for managing all applications on a server. Supports Laravel, MERN/MEAN/MEVN, Python (Django/FastAPI/Flask), and Java (Spring Boot) projects across multiple projects and folders.

Two entry points exist: a bootstrap script that runs on the server itself, and a local CLI that provisions a remote server over SSH. Both converge on the same 5-step execution engine.

---

## Users

- **Developers** setting up local or staging environments
- **DevOps / sysadmins** provisioning fresh cloud VMs or bare-metal servers

---

## Architecture: Plugin-Based Engine

The system is split into a core orchestration engine, pluggable environment adapters, pluggable stack layers, and a shared verifier. The key design principle: **stack layers are independent and composable** (Database + Backend + Frontend selected separately), and **the OS/environment is detected first** before any installation begins.

### Execution Flow (5 Steps)

```
Entry Point (Bootstrap Script OR Local CLI + SSH)
    ↓
Core Engine (SSH · Docker API · Config loader · Logger · Progress tracker)
    ↓
STEP 1 — OS / Environment Detection
    → uname · /etc/os-release · docker info · WinRM ping · panel detection
    ↓
STEP 2 — Environment Adapter loads (Ubuntu / Docker / Windows)
    → adapter provides native primitives: package install, service management, port rules
    ↓
STEP 3 — API-Based Verification → Stack Auto-Selection
    → HTTP probe to project API endpoint or file inspection
    → parses: framework · runtime · versions · frontend type
    → Backend + Frontend are auto-selected from response
    → Database is configured interactively via Web UI dialog (see below)
    ↓
STEP 4 — Stack Installation (using selected adapter)
    4a. Database layer
    4b. Backend layer
    4c. Frontend layer
    ↓
STEP 5 — Post-Installation Checks + Monitoring (optional)
    → Deployment Report generated
```

---

## Step 3 Detail: Database Web UI Dialog

Database configuration is the **only manual step** in the flow. It is handled interactively in the web dashboard because users may have backups, existing credentials, or external providers. The engine pauses and waits for the user to confirm before proceeding.

**Option A — Local Install**
- Engine installs DB server on the target (MySQL, PostgreSQL, MongoDB)
- User selects: engine, version, root password, database name, app username

**Option B — External Provider**
- User supplies connection parameters: host, port, username, password, database name
- Supported providers: Supabase, PlanetScale, Atlas (MongoDB), AWS RDS, Neon
- Engine validates connection before proceeding

**Option C — Restore from Backup** *(optional, works with A or B)*
- User uploads a `.sql` / `.dump` / `.gz` file or provides a remote URL
- Engine auto-restores after DB is ready
- Connection test is performed before proceeding to Step 4

Once confirmed, credentials are written to `.env` on the target server and the engine resumes.

---

## Environment Adapters

Each adapter exposes a common interface used by all stack layers:

```python
class BaseAdapter:
    def detect(self) -> bool: ...          # returns True if this env matches
    def install_packages(packages): ...
    def start_service(name): ...
    def enable_service(name): ...
    def open_port(port, protocol): ...
    def write_file(path, content): ...
    def run(command) -> str: ...
    def get_info(self) -> dict: ...
```

| Adapter | Mechanism | Key tools |
|---|---|---|
| Ubuntu | SSH (Paramiko) | apt, systemd, ufw, Certbot, nginx |
| Docker | Docker SDK / compose | Dockerfile generator, docker-compose, volumes, networks |
| Windows | WinRM (pywinrm) | Chocolatey, PowerShell, IIS |

---

## Stack Layers

Stack layers are **independently selectable**. Named presets (MERN, MEAN, MEVN, Laravel+React, Django+React) expand into the 3-layer config automatically.

### Database Layer
| Mode | Engines |
|---|---|
| Local install | MySQL, PostgreSQL, MongoDB, SQLite (dev only) |
| External provider | Supabase, PlanetScale, Atlas, AWS RDS, Neon |

### Backend Layer
| Framework | Runtime | Key tools |
|---|---|---|
| Laravel | PHP 8.x | Composer, artisan, Queue, Scheduler |
| Node / Express | Node.js LTS | npm, PM2, REST/GraphQL |
| Django / FastAPI / Flask | Python 3.11+ | pip, venv, gunicorn |
| Spring Boot | Java 17/21 | Maven / Gradle, Tomcat / runnable JAR |

All backends are served via nginx reverse proxy (or IIS on Windows).

### Frontend Layer
| Type | Options |
|---|---|
| SPA | React, Vue, Angular — built with Vite, served via nginx |
| SSR | Next.js, Nuxt, Blade (Laravel), Jinja2 (Django) |
| None | API-only mode — frontend step skipped |

---

## Named Presets

Presets are shorthand in `installer.yaml` that expand to a full 3-layer config:

| Preset | Database | Backend | Frontend |
|---|---|---|---|
| MERN | MongoDB (local) | Node/Express | React |
| MEAN | MongoDB (local) | Node/Express | Angular |
| MEVN | MongoDB (local) | Node/Express | Vue |
| Laravel+React | MySQL (local) | Laravel | React |
| Laravel+Vue | MySQL (local) | Laravel | Vue |
| Laravel+Blade | MySQL (local) | Laravel | Blade (SSR) |
| Django+React | PostgreSQL (local) | Django | React |

All preset values can be overridden per-field in `installer.yaml`.

---

## Configuration Files

### `installer.yaml` (per-project)
```yaml
# Minimal example — preset expands automatically
preset: MERN
project_path: /var/www/myapp
domain: myapp.com
env_file: .env.production

# Override specific layers
database:
  engine: postgresql
  mode: external          # local | external
  # local options
  version: "16"
  db_name: myapp_db
  # external options
  host: db.example.com
  port: 5432
  user: myapp_user
  # backup (optional)
  backup_url: https://storage.example.com/backup.sql.gz

backend:
  framework: laravel
  php_version: "8.2"
  queue: true
  scheduler: true

frontend:
  framework: react
  build_tool: vite
  output_dir: dist

verify_api:
  url: "http://localhost:8000/api/health"
  method: GET
  expect_status: 200
  expect_json: { "status": "ok" }
  timeout: 30s
  retries: 3

monitoring:
  enabled: false
  ping_url: https://uptime.example.com/api/push/abc123
  log_rotation: true
  alert_webhook: https://hooks.slack.com/...
```

### `manifest.yaml` (central registry)
```yaml
projects:
  - name: myapp
    config: /path/to/myapp/installer.yaml
    servers:
      - host: 192.168.1.10
        user: ubuntu
        key: ~/.ssh/id_rsa
  - name: blog
    config: /path/to/blog/installer.yaml
    servers:
      - host: 192.168.1.20
        user: root
        password_env: BLOG_SERVER_PASS
```

---

## CLI Commands

| Command | Description |
|---|---|
| `installer detect` | Probe target OS/env and print a report |
| `installer init` | Generate `installer.yaml` for a project interactively |
| `installer install` | Full 5-step install flow |
| `installer install --step 3` | Run a specific step only |
| `installer verify` | Run pre-flight or post-install checks only |
| `installer status` | Show running services and app health |
| `installer deploy` | Re-deploy app code without full reinstall |
| `installer dashboard` | Launch web UI on port 8080 |
| `installer list` | List all projects in manifest |

---

## Web Dashboard

A FastAPI app served on port 8080, launched via `installer dashboard` or automatically during install when `--ui` flag is passed. The UI follows an **app store pattern** — five sections in a persistent left sidebar, a search bar, and a content pane that updates without page reload.

### Navigation sections

#### Explore
Browse all available stack presets as cards. Each card shows the stack icon, name, tag row (runtime badges), and key tools. Filters across the top narrow by runtime (PHP, Node.js, Python, Java, Docker). A "+ Custom stack" card opens the manual `installer init` wizard.

Presets available: MERN, MEAN, MEVN, Laravel+React, Laravel+Vue, Laravel+Blade, Django+React, Spring Boot, and any user-defined entries in `manifest.yaml`.

#### Installed
Lists every app installed on the currently connected server. Each row shows: app name + stack, install path, runtime versions, a live status dot (running / degraded / stopped), and per-app action buttons — **Update**, **Clone**, and **Verify** (highlighted on degraded apps).

#### Verify
Select an installed app from a dropdown and run verification. Displays two check groups:

- **System checks** — services running, ports open, SSL certificate expiry, DB connectivity, queue/worker process
- **API health check** — HTTP call to the configured `verify_api.url`, response status, JSON field assertion

Each check shows pass / warn / fail with a detail value. A summary badge row at the bottom counts totals. Failed checks link to a suggested fix command.

#### Updates
Shows apps with available runtime or dependency upgrades. Each update row shows current → target version, a changelog button, and an individual **Update** button. Security updates are flagged with a red badge. An **Update all** button at the top triggers a batch upgrade. Apps already up to date are shown below in a dimmed section.

#### Clone
Duplicates an existing installation to a new folder or a different server. Fields:
- Source app (dropdown of installed apps)
- Target folder (text input, e.g. `/var/www/myapp-staging`)
- Target server (same server or select from manifest, or add new)
- Database mode: clone with empty DB, copy database, or configure external

A warning banner reminds the user to review `.env` credentials before starting. Cloning reuses the source `installer.yaml` with the target path and DB overrides applied.

### Always-present elements

- **Server indicator** at the bottom of the sidebar shows the connected server IP and live status dot
- **Real-time log panel** slides up during any active install, update, clone, or verify operation — WebSocket-streamed, with step progress indicator (Steps 1–5)
- **Deployment report** accessible after every install or update run

---

## Project Structure

```
installer/
├── installer/
│   ├── cli.py                  # Click CLI entry point
│   ├── core/
│   │   ├── engine.py           # Orchestrator — runs the 5-step flow
│   │   ├── ssh.py              # Paramiko SSH client
│   │   ├── docker.py           # Docker SDK client
│   │   ├── winrm.py            # pywinrm client
│   │   ├── detector.py         # Step 1: OS/env detection
│   │   ├── config.py           # installer.yaml + manifest loader
│   │   ├── logger.py           # Structured logger (file + stream)
│   │   └── progress.py         # Job/step progress tracker
│   ├── adapters/
│   │   ├── base.py             # BaseAdapter interface
│   │   ├── ubuntu.py
│   │   ├── docker.py
│   │   └── windows.py
│   ├── stacks/
│   │   ├── db/
│   │   │   ├── base.py         # BaseDBLayer interface
│   │   │   ├── mysql.py
│   │   │   ├── postgres.py
│   │   │   ├── mongodb.py
│   │   │   └── external.py     # connects to external provider
│   │   ├── backend/
│   │   │   ├── base.py         # BaseBackend interface
│   │   │   ├── laravel.py
│   │   │   ├── node.py
│   │   │   ├── python_app.py
│   │   │   └── java.py
│   │   ├── frontend/
│   │   │   ├── base.py         # BaseFrontend interface
│   │   │   ├── react.py
│   │   │   ├── vue.py
│   │   │   ├── angular.py
│   │   │   └── ssr.py          # Blade, Jinja2, Next.js, Nuxt
│   │   └── presets.py          # preset → layer config expansion
│   ├── verifier/
│   │   ├── engine.py           # runs pre-flight + post-install checks
│   │   ├── api_check.py        # Step 3 + Step 5 HTTP API probe
│   │   └── system_check.py     # ports, services, DB conn, SSL
│   └── web/
│       ├── server.py           # FastAPI app + route registration
│       ├── ws.py               # WebSocket log streaming
│       ├── static/
│       │   ├── app.js          # SPA nav, section switching
│       │   └── style.css
│       └── templates/
│           ├── base.html       # Shell: sidebar + topbar + content pane
│           ├── explore.html    # Preset card grid + runtime filters
│           ├── installed.html  # Installed app rows + status dots
│           ├── verify.html     # Check groups + pass/warn/fail rows
│           ├── updates.html    # Update rows + batch update
│           ├── clone.html      # Clone form + warning banner
│           └── db_config.html  # Step 3 DB interactive dialog
├── bootstrap.sh                # curl | bash entry point
├── pyproject.toml
├── installer.yaml.example
└── manifest.yaml.example
```

---

## Stack Interfaces

```python
# stacks/backend/base.py
class BaseBackend:
    def __init__(self, adapter: BaseAdapter, config: dict): ...
    def preflight(self): ...        # check prerequisites
    def install(self): ...          # install runtime + packages
    def configure(self): ...        # write config files, .env
    def deploy(self, path): ...     # deploy app code
    def start(self): ...            # start service / process manager

# stacks/db/base.py
class BaseDBLayer:
    def __init__(self, adapter: BaseAdapter, config: dict): ...
    def install_local(self): ...    # only for local mode
    def connect_external(self): ... # only for external mode
    def test_connection(self) -> bool: ...
    def restore_backup(self, source): ...
    def write_env(self, env_path): ...

# verifier/api_check.py
class APICheck:
    def probe(self, url, method, expect_status, expect_json,
              timeout, retries, headers) -> CheckResult: ...
```

---

## Entry Points

### Bootstrap Script (`bootstrap.sh`)
```bash
#!/bin/bash
# Installs Python 3.11+, pip, the installer package, then starts the web UI
curl -fsSL https://raw.githubusercontent.com/.../bootstrap.sh | bash
# Opens http://<server-ip>:8080 for interactive setup
```

### Local CLI + SSH
```bash
pip install installer-tool
installer install --host 192.168.1.10 --user ubuntu --key ~/.ssh/id_rsa
# Or using manifest:
installer install --project myapp
```

---

## Deployment Report

Generated at the end of every install run:

```json
{
  "project": "myapp",
  "timestamp": "2026-06-29T14:30:00Z",
  "os_detected": "Ubuntu 24.04",
  "adapter": "ubuntu",
  "stack": {
    "database": { "engine": "postgresql", "mode": "local", "version": "16" },
    "backend":  { "framework": "laravel", "php": "8.2" },
    "frontend": { "framework": "react", "build_tool": "vite" }
  },
  "steps": [
    { "step": 1, "name": "OS Detection",     "status": "pass" },
    { "step": 2, "name": "Adapter Load",     "status": "pass" },
    { "step": 3, "name": "API Verification", "status": "pass", "response_time_ms": 142 },
    { "step": 4, "name": "Installation",     "status": "pass" },
    { "step": 5, "name": "Post Checks",      "status": "pass" }
  ],
  "api_check": { "url": "/api/health", "status": 200, "json": { "status": "ok" } },
  "issues": []
}
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `click` | CLI framework |
| `paramiko` | SSH client |
| `docker` | Docker SDK |
| `pywinrm` | WinRM for Windows |
| `fastapi` + `uvicorn` | Web dashboard server |
| `httpx` | API verification HTTP client |
| `pydantic` | Config validation |
| `rich` | Terminal progress/logging UI |
| `pyyaml` | YAML config parsing |
| `python-dotenv` | .env file management |
