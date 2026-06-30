import click

@click.group()
def cli():
    """Installer/verifier tool for deploying web apps to Ubuntu, Docker, and Windows servers."""
    pass

@cli.command()
@click.option("--host", default=None, help="Remote host to probe")
@click.option("--user", default=None, help="SSH username")
@click.option("--key", default=None, help="SSH private key path")
def detect(host, user, key):
    """Probe target OS/environment and print a report."""
    click.echo("detect: not yet implemented")

@cli.command(name="init")
@click.option("--project-path", default=".", help="Path to the project")
def init(project_path):
    """Generate installer.yaml for a project interactively."""
    click.echo("init: not yet implemented")

@cli.command()
@click.option("--config", default="installer.yaml", help="Path to installer.yaml")
@click.option("--host", default=None, help="Remote host")
@click.option("--user", default=None, help="SSH username")
@click.option("--key", default=None, help="SSH private key path")
@click.option("--project", default=None, help="Project name from manifest")
@click.option("--step", default=None, type=int, help="Run a specific step only (1-5)")
def install(config, host, user, key, project, step):
    """Run the full 5-step install flow."""
    click.echo("install: not yet implemented")

@cli.command()
@click.option("--config", default="installer.yaml", help="Path to installer.yaml")
@click.option("--host", default=None, help="Remote host")
@click.option("--user", default=None, help="SSH username")
@click.option("--key", default=None, help="SSH private key path")
def verify(config, host, user, key):
    """Run pre-flight or post-install checks."""
    click.echo("verify: not yet implemented")

@cli.command()
@click.option("--config", default="installer.yaml", help="Path to installer.yaml")
@click.option("--host", default=None, help="Remote host")
@click.option("--user", default=None, help="SSH username")
@click.option("--key", default=None, help="SSH private key path")
def status(config, host, user, key):
    """Show running services and app health."""
    click.echo("status: not yet implemented")

@cli.command()
@click.option("--config", default="installer.yaml", help="Path to installer.yaml")
@click.option("--host", default=None, help="Remote host")
@click.option("--user", default=None, help="SSH username")
@click.option("--key", default=None, help="SSH private key path")
def deploy(config, host, user, key):
    """Re-deploy app code without full reinstall."""
    click.echo("deploy: not yet implemented")

@cli.command()
@click.option("--port", default=8080, help="Port to run the dashboard on")
def dashboard(port):
    """Launch the web UI dashboard."""
    click.echo("dashboard: not yet implemented")

@cli.command(name="list")
@click.option("--manifest", default="manifest.yaml", help="Path to manifest.yaml")
def list_projects(manifest):
    """List all projects in the manifest."""
    click.echo("list: not yet implemented")
