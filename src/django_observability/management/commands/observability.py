"""Unified observability management command using Click."""

import shutil
import socket
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import click
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Manage observability stack and verify setup."""

    help = "Manage observability stack (start/stop/check)"

    def add_arguments(self, parser):
        """Add arguments - Click handles the real parsing."""
        parser.add_argument("command", nargs="?", help="Subcommand (stack, check)")
        parser.add_argument("subargs", nargs="*", help="Subcommand arguments")

    def handle(self, *args, **options):
        """Delegate to Click command group."""
        # Build args list for Click
        cli_args = []
        if options.get("command"):
            cli_args.append(options["command"])
        if options.get("subargs"):  # pragma: no cover
            cli_args.extend(options["subargs"])

        try:
            cli(args=cli_args, standalone_mode=False, obj={"stdout": self.stdout})
        except click.ClickException as e:  # pragma: no cover
            e.show()
            raise SystemExit(e.exit_code)
        except SystemExit as e:  # pragma: no cover
            if e.code != 0:
                raise


@click.group()
@click.pass_context
def cli(ctx):
    """Manage Django observability stack and configuration."""
    ctx.ensure_object(dict)


# =============================================================================
# Stack Management Commands
# =============================================================================


@cli.group()
def stack():
    """Manage the local observability stack (Grafana, Tempo, etc.)."""
    pass


@stack.command()
@click.option(
    "--app-url",
    default="host.docker.internal:8000",
    help="URL where Django app exposes /metrics endpoint",
    show_default=True,
)
def start(app_url):
    """Start the observability stack using Docker Compose.

    Examples:

      # App running on host (default)
      python manage.py observability stack start

      # App running on localhost
      python manage.py observability stack start --app-url localhost:8000

      # App running in Docker
      python manage.py observability stack start --app-url django-app:8000
    """
    if not _check_docker_compose():  # pragma: no cover
        raise SystemExit(1)

    click.secho("=" * 60, fg="cyan")
    click.secho("Starting Observability Stack", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")
    click.echo()

    work_dir = _get_work_dir(app_url)
    cmd = _get_compose_cmd()

    click.echo(f"Using configs from: {work_dir}")
    if app_url:  # pragma: no branch
        click.echo(f"Prometheus will scrape metrics from: {app_url}")
    click.echo("Starting Docker containers...")

    try:
        subprocess.run(
            cmd + ["-f", "docker-compose.yml", "up", "-d"],
            cwd=work_dir,
            check=True,
        )
    except subprocess.CalledProcessError as e:  # pragma: no cover
        click.secho(f"Failed to start services: {e}", fg="red", err=True)
        raise SystemExit(1)

    click.echo()
    click.secho("Observability stack started!", fg="green", bold=True)
    click.echo()
    _print_service_urls()
    click.echo()
    _print_next_steps()


@stack.command()
def stop():
    """Stop the observability stack."""
    if not _check_docker_compose():  # pragma: no cover
        raise SystemExit(1)

    click.echo("Stopping observability stack...")

    work_dir = _get_work_dir()
    cmd = _get_compose_cmd()

    try:
        subprocess.run(
            cmd + ["-f", "docker-compose.yml", "down"],
            cwd=work_dir,
            check=True,
        )
        click.secho("Stack stopped successfully", fg="green")
    except subprocess.CalledProcessError as e:  # pragma: no cover
        click.secho(f"Failed to stop services: {e}", fg="red", err=True)
        raise SystemExit(1)


@stack.command()
@click.option(
    "--app-url",
    default="host.docker.internal:8000",
    help="URL where Django app exposes /metrics endpoint",
    show_default=True,
)
def restart(app_url):
    """Restart the observability stack."""
    if not _check_docker_compose():  # pragma: no cover
        raise SystemExit(1)

    click.echo("Restarting observability stack...")
    work_dir = _get_work_dir(app_url)
    cmd = _get_compose_cmd()

    try:
        # Stop
        subprocess.run(
            cmd + ["-f", "docker-compose.yml", "down"],
            cwd=work_dir,
            check=True,
        )
        # Start
        subprocess.run(
            cmd + ["-f", "docker-compose.yml", "up", "-d"],
            cwd=work_dir,
            check=True,
        )
        click.secho("Stack restarted successfully", fg="green")
    except subprocess.CalledProcessError as e:  # pragma: no cover
        click.secho(f"Failed to restart services: {e}", fg="red", err=True)
        raise SystemExit(1)


@stack.command()
def status():
    """Show status of running services."""
    if not _check_docker_compose():  # pragma: no cover
        raise SystemExit(1)

    work_dir = _get_work_dir()
    cmd = _get_compose_cmd()

    try:
        subprocess.run(
            cmd + ["-f", "docker-compose.yml", "ps"],
            cwd=work_dir,
            check=True,
        )
    except subprocess.CalledProcessError as e:  # pragma: no cover
        click.secho(f"Failed to get status: {e}", fg="red", err=True)
        raise SystemExit(1)


@stack.command()
@click.option(
    "--follow/--no-follow",
    "-f",
    default=False,
    help="Follow log output",
)
@click.option(
    "--tail",
    default=50,
    type=int,
    help="Number of lines to show from the end",
    show_default=True,
)
def logs(follow, tail):
    """Show logs from observability services."""
    if not _check_docker_compose():  # pragma: no cover
        raise SystemExit(1)

    work_dir = _get_work_dir()
    cmd = _get_compose_cmd()

    args = cmd + ["-f", "docker-compose.yml", "logs", f"--tail={tail}"]
    if follow:  # pragma: no cover
        args.append("-f")

    try:
        subprocess.run(args, cwd=work_dir)
    except KeyboardInterrupt:  # pragma: no cover
        click.echo("\nLogs stopped")
    except subprocess.CalledProcessError as e:  # pragma: no cover
        click.secho(f"Failed to show logs: {e}", fg="red", err=True)
        raise SystemExit(1)


# =============================================================================
# Health Check Command
# =============================================================================


@cli.command()
def check():
    """Verify Django Observability setup and connectivity.

    Checks:
      - Configuration is loaded correctly
      - OTLP endpoint is reachable
      - Required packages are installed
      - Creates a test trace to verify tracing works
    """
    click.secho("=" * 60, fg="cyan")
    click.secho("Django Observability Health Check", fg="cyan", bold=True)
    click.secho("=" * 60, fg="cyan")
    click.echo()

    ok_count = 0
    warning_count = 0
    error_count = 0

    # Check 1: Configuration
    click.secho("Configuration:", fg="cyan", bold=True)
    result = _check_configuration()
    ok_count += result[0]
    warning_count += result[1]
    error_count += result[2]
    click.echo()

    # Check 2: OTLP Endpoint
    click.secho("OTLP Endpoint:", fg="cyan", bold=True)
    result = _check_otlp_endpoint()
    ok_count += result[0]
    warning_count += result[1]
    error_count += result[2]
    click.echo()

    # Check 3: Installed Packages
    click.secho("Installed Packages:", fg="cyan", bold=True)
    result = _check_packages()
    ok_count += result[0]
    warning_count += result[1]
    error_count += result[2]
    click.echo()

    # Check 4: Test Trace
    click.secho("Test Trace:", fg="cyan", bold=True)
    result = _test_trace()
    ok_count += result[0]
    warning_count += result[1]
    error_count += result[2]
    click.echo()

    # Summary
    click.secho("=" * 60, fg="cyan")
    summary = f"Summary: {ok_count} OK"
    if warning_count > 0:  # pragma: no cover
        summary += f", {warning_count} WARNING"
    if error_count > 0:  # pragma: no cover
        summary += f", {error_count} ERROR"

    if error_count > 0:  # pragma: no cover
        click.secho(summary, fg="red", bold=True)
        click.secho("=" * 60, fg="cyan")
        raise SystemExit(1)
    elif warning_count > 0:  # pragma: no cover
        click.secho(summary, fg="yellow", bold=True)
    else:
        click.secho(summary, fg="green", bold=True)

    click.secho("=" * 60, fg="cyan")


# =============================================================================
# Helper Functions
# =============================================================================


def _check_docker_compose():
    """Check if docker-compose is available."""
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return True

        result = subprocess.run(  # pragma: no cover
            ["docker-compose", "version"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:  # pragma: no cover
            return True

        click.secho(  # pragma: no cover
            "Docker Compose not found. Please install Docker and Docker Compose:",
            fg="red",
            err=True,
        )
        click.echo(
            "https://docs.docker.com/compose/install/", err=True
        )  # pragma: no cover
        return False  # pragma: no cover
    except FileNotFoundError:  # pragma: no cover
        click.secho(
            "Docker not found. Please install Docker:",
            fg="red",
            err=True,
        )
        click.echo("https://docs.docker.com/get-docker/", err=True)
        return False


def _get_compose_cmd():
    """Get the appropriate docker compose command."""
    result = subprocess.run(
        ["docker", "compose", "version"],
        capture_output=True,
    )
    if result.returncode == 0:
        return ["docker", "compose"]
    else:  # pragma: no cover
        return ["docker-compose"]


def _get_work_dir(app_url=None):
    """Get or create working directory and copy stack configs."""
    work_dir = Path.home() / ".django-observability"
    work_dir.mkdir(exist_ok=True)

    # Copy stack files from package to work directory
    try:
        stack_path = (
            Path(__file__).parent.parent.parent / "management" / "commands" / "stack"
        )

        if stack_path.exists():
            for config_file in stack_path.glob("*"):
                if config_file.is_file():
                    dest = work_dir / config_file.name

                    # For prometheus.yml, customize the target URL
                    if (
                        config_file.name == "prometheus.yml" and app_url
                    ):  # pragma: no cover
                        content = config_file.read_text()
                        content = content.replace(
                            "['host.docker.internal:8000']", f"['{app_url}']"
                        )
                        dest.write_text(content)
                    else:
                        shutil.copy(config_file, dest)
    except Exception as e:  # pragma: no cover
        click.secho(f"Warning: Could not copy stack files: {e}", fg="yellow")

    return work_dir


def _print_service_urls():
    """Print URLs for accessing services."""
    click.secho("Service URLs:", fg="cyan", bold=True)
    click.echo("  Grafana:    http://localhost:3000 (no login required)")
    click.echo("  Prometheus: http://localhost:9090")
    click.echo("  Tempo:      http://localhost:3200")
    click.echo("  Loki:       http://localhost:3100")
    click.echo("  Pyroscope:  http://localhost:4040")
    click.echo("  Alloy UI:   http://localhost:12345")


def _print_next_steps():
    """Print next steps for user."""
    click.secho("Next Steps:", fg="cyan", bold=True)
    click.echo()
    click.echo("1. Wait ~10 seconds for dashboards to import automatically")
    click.echo()
    click.echo("2. Your app should export OTLP to http://localhost:4317")
    click.echo("   (This is the default in django-observability)")
    click.echo()
    click.echo("3. Start your Django application:")
    click.echo("   python manage.py runserver")
    click.echo()
    click.echo("4. Generate some traffic:")
    click.echo("   curl http://localhost:8000/")
    click.echo()
    click.echo("5. Verify setup:")
    click.echo("   python manage.py observability check")
    click.echo()
    click.echo("6. Open Grafana to see dashboards & explore!")
    click.echo("   http://localhost:3000")
    click.echo("   Dashboards: Django Overview, Django Requests, Celery Tasks")
    click.echo()
    click.echo("7. To stop:")
    click.echo("   python manage.py observability stack stop")


def _check_configuration():
    """Check configuration is loaded correctly."""
    ok, warn, err = 0, 0, 0

    try:
        from django_observability.conf import get_observability_config

        config = get_observability_config()

        service = config.get("SERVICE_NAME", "unknown")
        click.echo(f"  Service: {service}")
        ok += 1

        # Tracing
        if config.get("TRACING", {}).get("ENABLED"):
            sample_rate = config["TRACING"].get("SAMPLE_RATE", 1.0)
            click.secho(
                f"  ✅ Tracing enabled ({sample_rate * 100:.0f}% sampling)",
                fg="green",
            )
            ok += 1
        else:  # pragma: no cover
            click.secho("  ⚠️  Tracing disabled", fg="yellow")
            warn += 1

        # Logging
        if config.get("LOGGING", {}).get("ENABLED"):
            fmt = config["LOGGING"].get("FORMAT", "console")
            click.secho(f"  ✅ Logging enabled ({fmt} format)", fg="green")
            ok += 1
        else:  # pragma: no cover
            click.secho("  ⚠️  Logging disabled", fg="yellow")
            warn += 1

        # Celery
        if config.get("CELERY", {}).get("ENABLED"):  # pragma: no cover
            click.secho("  ✅ Celery enabled", fg="green")
            ok += 1

        # Profiling
        if config.get("PROFILING", {}).get("ENABLED"):  # pragma: no cover
            url = config["PROFILING"].get("PYROSCOPE_URL")
            click.secho(f"  ✅ Profiling enabled ({url})", fg="green")
            ok += 1

    except Exception as e:  # pragma: no cover
        click.secho(f"  ❌ Failed to load config: {e}", fg="red")
        err += 1

    return ok, warn, err


def _check_otlp_endpoint():
    """Check OTLP endpoint connectivity."""
    ok, warn, err = 0, 0, 0

    try:
        from django_observability.conf import get_observability_config

        config = get_observability_config()

        endpoint = config.get("TRACING", {}).get("OTLP_ENDPOINT")
        if not endpoint:  # pragma: no cover
            click.secho("  ⚠️  No OTLP endpoint configured", fg="yellow")
            warn += 1
            return ok, warn, err

        click.echo(f"  Endpoint: {endpoint}")

        # Parse endpoint
        parsed = urlparse(endpoint)
        host = parsed.hostname or "localhost"
        port = parsed.port or 4317

        # Try to connect
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                click.secho(f"  ✅ Reachable ({host}:{port})", fg="green")
                ok += 1
            else:  # pragma: no cover
                click.secho(
                    f"  ❌ Not reachable ({host}:{port})\n"
                    f"     Make sure OTLP receiver is running",
                    fg="red",
                )
                err += 1
        except Exception as e:  # pragma: no cover
            click.secho(f"  ❌ Connection test failed: {e}", fg="red")
            err += 1

    except Exception as e:  # pragma: no cover
        click.secho(f"  ❌ Endpoint check failed: {e}", fg="red")
        err += 1

    return ok, warn, err


def _check_packages():
    """Check installed packages."""
    import importlib

    ok, warn, err = 0, 0, 0

    packages = [
        ("opentelemetry.api", "opentelemetry-api", "Core tracing"),
        (
            "opentelemetry.instrumentation.django",
            "opentelemetry-instrumentation-django",
            "Django instrumentation",
        ),
        (
            "opentelemetry.instrumentation.celery",
            "opentelemetry-instrumentation-celery",
            "Celery tracing",
        ),
        ("pyroscope", "pyroscope-io", "Profiling"),
        ("django_prometheus", "django-prometheus", "Prometheus metrics"),
    ]

    for module, package, desc in packages:
        try:
            importlib.import_module(module)
            click.secho(f"  ✅ {package}: {desc}", fg="green")
            ok += 1
        except ImportError:
            click.secho(
                f"  ⚠️  {package}: {desc} (not installed)\n"
                f"     → Run: pip install {package}",
                fg="yellow",
            )
            warn += 1

    return ok, warn, err


def _test_trace():
    """Create a test trace to verify tracing works."""
    ok, warn, err = 0, 0, 0

    try:
        from opentelemetry import trace

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("observability-check-test") as span:
            ctx = span.get_span_context()

            if ctx.trace_id:
                trace_id = format(ctx.trace_id, "032x")
                span_id = format(ctx.span_id, "016x")

                click.secho("  ✅ Created test span", fg="green")
                click.echo(f"     Trace ID: {trace_id}")
                click.echo(f"     Span ID: {span_id}")
                ok += 1

                from django_observability.conf import get_observability_config

                config = get_observability_config()
                endpoint = config.get("TRACING", {}).get("OTLP_ENDPOINT", "")

                if (
                    "localhost" in endpoint or "127.0.0.1" in endpoint
                ):  # pragma: no branch
                    click.echo(
                        f"\n     Check in Tempo:\n"
                        f"     http://localhost:3200/api/traces/{trace_id}"
                    )
            else:  # pragma: no cover
                click.secho("  ⚠️  Span created but no trace ID", fg="yellow")
                warn += 1

    except Exception as e:  # pragma: no cover
        click.secho(f"  ❌ Failed to create test trace: {e}", fg="red")
        err += 1

    return ok, warn, err
