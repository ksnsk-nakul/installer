from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from installer.core.config import load_config, load_manifest
from installer.core.logger import get_logger

console = Console()
logger = get_logger("installer.cli")


def _make_runner(host: Optional[str], user: Optional[str], key: Optional[str]):
    """Return an SSHClient for remote targets, or a local runner for localhost."""
    if host:
        from installer.core.ssh import SSHClient
        client = SSHClient(host=host, user=user or "root", key_path=key)
        client.connect()
        return client

    # Local runner — runs commands via subprocess
    import subprocess

    class LocalRunner:
        def run(self, command: str) -> str:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip())
            return result.stdout

        def write_file(self, path: str, content: str) -> None:
            Path(path).write_text(content)

    return LocalRunner()


@click.group()
def cli():
    """Installer/verifier tool for deploying web apps to Ubuntu, Docker, and Windows servers."""


@cli.command()
@click.option("--host", default=None, help="Remote host to probe")
@click.option("--user", default=None, help="SSH username")
@click.option("--key", default=None, help="SSH private key path")
def detect(host, user, key):
    """Probe target OS/environment and print a report."""
    from installer.core.detector import detect_environment

    runner = _make_runner(host, user, key)
    env, info = detect_environment(runner)
    console.print(f"[bold]Environment:[/bold] {env.value}")
    for k, v in info.items():
        console.print(f"  {k}: {v}")


@cli.command(name="init")
@click.option("--project-path", default=".", help="Path to the project")
@click.option("--output", default="installer.yaml", help="Output file path")
def init(project_path, output):
    """Generate installer.yaml for a project interactively."""
    console.print("[bold]installer init[/bold] — interactive config generator")

    preset = click.prompt(
        "Preset",
        type=click.Choice(["MERN", "MEAN", "MEVN", "LARAVEL_REACT", "LARAVEL_VUE",
                           "LARAVEL_BLADE", "DJANGO_REACT", "SPRINGBOOT", "custom"]),
        default="MERN",
    )
    domain = click.prompt("Domain", default="example.com")
    env_file = click.prompt(".env file name", default=".env")

    lines = [
        f"preset: {preset}" if preset != "custom" else "# configure stack below",
        f"project_path: {project_path}",
        f"domain: {domain}",
        f"env_file: {env_file}",
    ]
    Path(output).write_text("\n".join(lines) + "\n")
    console.print(f"[green]Written:[/green] {output}")


@cli.command()
@click.option("--config", default="installer.yaml", help="Path to installer.yaml")
@click.option("--host", default=None, help="Remote host")
@click.option("--user", default=None, help="SSH username")
@click.option("--key", default=None, help="SSH private key path")
@click.option("--project", default=None, help="Project name from manifest")
@click.option("--manifest", default="manifest.yaml", help="Path to manifest.yaml")
@click.option("--step", default=None, type=int, help="Run a specific step only (1-5)")
@click.option("--report-out", default=None, help="Write JSON deployment report to file")
def install(config, host, user, key, project, manifest, step, report_out):
    """Run the full 5-step install flow."""
    from installer.core.engine import Engine

    # Resolve config + runner from --project or direct --config/--host flags
    if project:
        manifest_cfg = load_manifest(manifest)
        entry = next((p for p in manifest_cfg.projects if p.name == project), None)
        if not entry:
            console.print(f"[red]Project '{project}' not found in {manifest}[/red]")
            sys.exit(1)
        cfg = load_config(entry.config)
        srv = entry.servers[0] if entry.servers else None
        runner = _make_runner(
            srv.host if srv else None,
            srv.user if srv else None,
            srv.key if srv else None,
        )
    else:
        cfg = load_config(config)
        runner = _make_runner(host, user, key)

    engine = Engine(cfg, runner)
    try:
        report = engine.run()
        if report_out:
            Path(report_out).write_text(json.dumps(report, indent=2))
            console.print(f"[green]Report written to {report_out}[/green]")
        else:
            console.print_json(json.dumps(report))
    except Exception as exc:
        console.print(f"[red]Install failed: {exc}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--config", default="installer.yaml", help="Path to installer.yaml")
@click.option("--host", default=None, help="Remote host")
@click.option("--user", default=None, help="SSH username")
@click.option("--key", default=None, help="SSH private key path")
def verify(config, host, user, key):
    """Run post-install system and API checks."""
    from installer.verifier.system_check import SystemCheck
    from installer.verifier.api_check import APICheck

    cfg = load_config(config)
    runner = _make_runner(host, user, key)

    sc = SystemCheck()
    results = sc.run(
        runner,
        domain=cfg.domain,
        db_engine=cfg.stack.database.engine,
        db_config=cfg.stack.database.model_dump(),
    )

    if cfg.verify_api:
        api_result = APICheck().probe(
            url=cfg.verify_api.url,
            method=cfg.verify_api.method,
            expect_status=cfg.verify_api.expect_status,
            expect_json=cfg.verify_api.expect_json,
            timeout=cfg.verify_api.timeout,
            retries=cfg.verify_api.retries,
        )
        from installer.verifier.system_check import SystemCheckResult
        results.append(SystemCheckResult(
            name="api_health", status=api_result.status, detail=api_result.detail
        ))

    table = Table(title="Verification Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status")
    table.add_column("Detail")
    for r in results:
        colour = {"pass": "green", "warn": "yellow", "fail": "red"}.get(r.status, "white")
        table.add_row(r.name, f"[{colour}]{r.status}[/{colour}]", r.detail)
    console.print(table)

    summary = SystemCheck.summary(results)
    console.print(f"pass={summary['pass']} warn={summary.get('warn',0)} fail={summary['fail']}")
    if summary["fail"] > 0:
        sys.exit(1)


@cli.command()
@click.option("--config", default="installer.yaml", help="Path to installer.yaml")
@click.option("--host", default=None, help="Remote host")
@click.option("--user", default=None, help="SSH username")
@click.option("--key", default=None, help="SSH private key path")
def status(config, host, user, key):
    """Show running services and app health."""
    from installer.verifier.system_check import SystemCheck

    cfg = load_config(config)
    runner = _make_runner(host, user, key)

    sc = SystemCheck()
    results = sc.run(runner, domain=cfg.domain)

    for r in results:
        colour = {"pass": "green", "warn": "yellow", "fail": "red"}.get(r.status, "white")
        console.print(f"[{colour}]{r.status:6}[/{colour}] {r.name}: {r.detail}")


@cli.command()
@click.option("--config", default="installer.yaml", help="Path to installer.yaml")
@click.option("--host", default=None, help="Remote host")
@click.option("--user", default=None, help="SSH username")
@click.option("--key", default=None, help="SSH private key path")
def deploy(config, host, user, key):
    """Re-deploy app code without full reinstall (runs Step 4 only)."""
    from installer.core.engine import Engine

    cfg = load_config(config)
    runner = _make_runner(host, user, key)
    engine = Engine(cfg, runner)

    console.print("[bold]Deploy:[/bold] re-running stack installation step")
    try:
        from installer.core.detector import detect_environment
        env, _ = detect_environment(runner)
        adapter = engine._load_adapter(env)
        from installer.stacks.presets import resolve_stack
        resolved = resolve_stack(cfg.stack, adapter)
        resolved.backend.run_all(cfg.project_path)
        resolved.frontend.run_all(cfg.project_path)
        console.print("[green]Deploy complete.[/green]")
    except Exception as exc:
        console.print(f"[red]Deploy failed: {exc}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8080, show_default=True)
@click.option("--reload", is_flag=True, default=False, help="Auto-reload on code changes")
def dashboard(host, port, reload):
    """Launch the web UI dashboard."""
    import uvicorn

    console.print(f"[bold]Dashboard:[/bold] http://{host}:{port}")
    uvicorn.run(
        "installer.web.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


@cli.command(name="list")
@click.option("--manifest", default="manifest.yaml", help="Path to manifest.yaml")
def list_projects(manifest):
    """List all projects registered in the manifest."""
    try:
        cfg = load_manifest(manifest)
    except FileNotFoundError:
        console.print(f"[red]manifest.yaml not found at {manifest}[/red]")
        sys.exit(1)

    if not cfg.projects:
        console.print("[dim]No projects registered.[/dim]")
        return

    table = Table(title="Registered Projects")
    table.add_column("Name", style="bold cyan")
    table.add_column("Config")
    table.add_column("Servers")
    for p in cfg.projects:
        servers = ", ".join(s.host for s in p.servers)
        table.add_row(p.name, p.config, servers)
    console.print(table)
