"""Unified o11y management command using Click."""

import os
import shutil
import socket
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import click
from django.core.management.base import BaseCommand
from django.urls import Resolver404, resolve

CELERY_EXPORTER_COMPOSE_FILE = "docker-compose.celery-exporter.yml"
CELERY_EXPORTER_PORT = 9808


class Command(BaseCommand):
    """Manage o11y stack and verify setup."""

    help = "Manage o11y stack (start/stop/check)"

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
            cli(args=cli_args, standalone_mode=False, obj={"stdout": self.stdout})  # pylint: disable=no-value-for-parameter
        except click.ClickException as e:  # pragma: no cover
            e.show()
            raise SystemExit(e.exit_code) from e
        except SystemExit as e:  # pragma: no cover
            if e.code != 0:
                raise


@click.group()
@click.pass_context
def cli(ctx):
    """Manage Django o11y stack and configuration."""
    ctx.ensure_object(dict)


@cli.group()
def stack():
    """Manage the local observability stack (Grafana, Tempo, etc.)."""


@stack.command()
@click.option(
    "--app-url",
    default="host.docker.internal:8000",
    help="URL where Django app exposes /metrics endpoint",
    show_default=True,
)
def start(app_url):
    """Start the o11y stack using Docker Compose.

    Examples:

      # App running on host (default)
      python manage.py o11y stack start

      # App running in Docker
      python manage.py o11y stack start --app-url django-app:8000
    """
    if not _check_docker_compose():  # pragma: no cover
        raise SystemExit(1)

    work_dir = _get_work_dir(app_url)
    cmd = _get_compose_cmd()
    compose_files = _get_compose_files(work_dir)

    click.echo(f"Starting stack (configs: {work_dir})...")

    try:
        subprocess.run(
            cmd + compose_files + ["up", "-d"],
            cwd=work_dir,
            check=True,
        )
    except subprocess.CalledProcessError as e:  # pragma: no cover
        click.secho(f"Failed to start services: {e}", fg="red", err=True)
        raise SystemExit(1) from e

    click.secho("Stack started.", fg="green")
    click.echo()
    _print_service_urls(work_dir)


@stack.command()
def stop():
    """Stop the observability stack."""
    if not _check_docker_compose():  # pragma: no cover
        raise SystemExit(1)

    click.echo("Stopping observability stack...")

    work_dir = _get_stack_dir()
    cmd = _get_compose_cmd()
    compose_files = _get_compose_files(work_dir)

    try:
        subprocess.run(
            cmd + compose_files + ["down"],
            cwd=work_dir,
            check=True,
        )
        click.secho("Stack stopped successfully", fg="green")
    except subprocess.CalledProcessError as e:  # pragma: no cover
        click.secho(f"Failed to stop services: {e}", fg="red", err=True)
        raise SystemExit(1) from e


@stack.command()
def restart():
    """Restart the observability stack without recreating containers."""
    if not _check_docker_compose():  # pragma: no cover
        raise SystemExit(1)

    click.echo("Restarting observability stack...")
    work_dir = _get_stack_dir()
    cmd = _get_compose_cmd()
    compose_files = _get_compose_files(work_dir)

    try:
        subprocess.run(
            cmd + compose_files + ["restart"],
            cwd=work_dir,
            check=True,
        )
        click.secho("Stack restarted.", fg="green")
    except subprocess.CalledProcessError as e:  # pragma: no cover
        click.secho(f"Failed to restart services: {e}", fg="red", err=True)
        raise SystemExit(1) from e


@stack.command()
def status():
    """Show status of running services."""
    if not _check_docker_compose():  # pragma: no cover
        raise SystemExit(1)

    work_dir = _get_stack_dir()
    cmd = _get_compose_cmd()
    compose_files = _get_compose_files(work_dir)

    try:
        subprocess.run(
            cmd + compose_files + ["ps"],
            cwd=work_dir,
            check=True,
        )
    except subprocess.CalledProcessError as e:  # pragma: no cover
        click.secho(f"Failed to get status: {e}", fg="red", err=True)
        raise SystemExit(1) from e


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

    work_dir = _get_stack_dir()
    cmd = _get_compose_cmd()
    compose_files = _get_compose_files(work_dir)

    args = cmd + compose_files + ["logs", f"--tail={tail}"]
    if follow:  # pragma: no cover
        args.append("-f")

    try:
        subprocess.run(args, cwd=work_dir, check=False)
    except KeyboardInterrupt:  # pragma: no cover
        click.echo("\nLogs stopped")
    except subprocess.CalledProcessError as e:  # pragma: no cover
        click.secho(f"Failed to show logs: {e}", fg="red", err=True)
        raise SystemExit(1) from e


@cli.command()
def check():
    """Verify Django O11y setup and connectivity.

    Checks:
      - Configuration is loaded correctly
      - OTLP endpoint is reachable
      - Required packages are installed
      - Creates a test trace to verify tracing works
    """
    ok_count = 0
    warning_count = 0
    error_count = 0

    click.secho("Configuration:", fg="cyan", bold=True)
    result = _check_configuration()
    ok_count += result[0]
    warning_count += result[1]
    error_count += result[2]

    click.secho("Metrics Endpoint:", fg="cyan", bold=True)
    result = _check_metrics_endpoint()
    ok_count += result[0]
    warning_count += result[1]
    error_count += result[2]

    click.secho("OTLP Endpoint:", fg="cyan", bold=True)
    result = _check_otlp_endpoint()
    ok_count += result[0]
    warning_count += result[1]
    error_count += result[2]

    click.secho("Installed Packages:", fg="cyan", bold=True)
    result = _check_packages()
    ok_count += result[0]
    warning_count += result[1]
    error_count += result[2]

    click.secho("Test Trace:", fg="cyan", bold=True)
    result = _test_trace()
    ok_count += result[0]
    warning_count += result[1]
    error_count += result[2]

    summary = f"{ok_count} OK"
    if warning_count > 0:  # pragma: no cover
        summary += f", {warning_count} warning"
    if error_count > 0:  # pragma: no cover
        summary += f", {error_count} error"
        click.secho(summary, fg="red")
        raise SystemExit(1)
    if warning_count > 0:  # pragma: no cover
        click.secho(summary, fg="yellow")
    else:
        click.secho(summary, fg="green")


def _get_broker_url() -> str | None:
    """Detect the Celery broker URL from Django or Celery settings."""

    from django.conf import settings

    # Env var takes precedence — lets callers override without changing settings.
    if broker_url := os.environ.get("CELERY_BROKER_URL"):
        return broker_url

    # Check Django-style Celery settings (CELERY_BROKER_URL)
    broker_url = getattr(settings, "CELERY_BROKER_URL", None)
    if broker_url:
        return broker_url

    # Check lowercase celery config (broker_url in CELERY dict or celeryconfig)
    celery_config = getattr(settings, "CELERY", {})
    if isinstance(celery_config, dict):
        broker_url = celery_config.get("broker_url")
        if broker_url:
            return broker_url

    # Try reading from the Celery app if it's already configured
    try:
        import celery as celery_module

        app = celery_module.current_app
        broker_url = app.conf.broker_url
        if broker_url and broker_url != "amqp://guest:guest@localhost//":
            return broker_url
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    return None


def _is_celery_enabled() -> bool:
    """Check if Celery is enabled in django-o11y settings."""
    try:
        from django_o11y.config.setup import get_o11y_config

        config = get_o11y_config()
        return bool(config.get("CELERY", {}).get("ENABLED"))
    except Exception:  # pylint: disable=broad-exception-caught
        return False


def _write_celery_exporter_override(work_dir: Path, broker_url: str) -> None:
    """Write a docker-compose override that adds celery-exporter."""
    compose_content = f"""\
services:
  celery-exporter:
    image: danihodovic/celery-exporter:latest
    command: --broker-url={broker_url}
    environment:
      # Buckets suited for async task durations (seconds → half-hours).
      # The Prometheus defaults (0.005–10 s) are designed for HTTP requests
      # and are too granular / too short for most Celery workloads.
      - CE_BUCKETS=1,2.5,5,10,30,60,300,600,900,1800
    ports:
      - "{CELERY_EXPORTER_PORT}:{CELERY_EXPORTER_PORT}"
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"
"""
    (work_dir / CELERY_EXPORTER_COMPOSE_FILE).write_text(compose_content)

    # Append a Prometheus scrape block to the Alloy config
    alloy_config = work_dir / "alloy-config.alloy"
    if alloy_config.exists():
        existing = alloy_config.read_text()
        scrape_block = f"""
// ============================================================
// Metrics: scrape celery-exporter /metrics → Prometheus
// ============================================================

prometheus.scrape "celery_exporter" {{
  targets = [
    {{
      "__address__" = "celery-exporter:{CELERY_EXPORTER_PORT}",
      "job"         = "celery-exporter",
    }},
  ]
  metrics_path    = "/metrics"
  scrape_interval = "15s"
  forward_to      = [prometheus.remote_write.default.receiver]
}}
"""
        if "celery_exporter" not in existing:
            alloy_config.write_text(existing + scrape_block)


def _validate_exporter_broker_url(broker_url: str) -> tuple[bool, str | None]:
    """Validate broker URL compatibility for celery-exporter container."""
    if not broker_url:
        return False, "broker URL is empty"

    parsed = urlparse(broker_url)
    scheme = (parsed.scheme or "").lower()

    if scheme in {"memory", "filesystem"}:
        return (
            False,
            f"unsupported broker transport '{scheme}://' for exporter container",
        )

    return True, None


def _rewrite_broker_url_for_container(broker_url: str) -> str:
    """Rewrite loopback broker URLs to host.docker.internal for container use.

    celery-exporter runs inside Docker, so localhost/127.0.0.1 would resolve
    to the container itself. The exporter compose override already adds
    host.docker.internal via extra_hosts, so we rewrite the host there.
    """
    parsed = urlparse(broker_url)
    host = (parsed.hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "::1"}:
        broker_url = broker_url.replace(
            parsed.hostname or host, "host.docker.internal", 1
        )
    return broker_url


def _get_compose_files(work_dir: Path) -> list[str]:
    """Return the list of -f flags for docker compose commands."""
    files = ["-f", "docker-compose.yml"]
    if (work_dir / CELERY_EXPORTER_COMPOSE_FILE).exists():
        files += ["-f", CELERY_EXPORTER_COMPOSE_FILE]
    return files


def _check_docker_compose():
    """Check if docker-compose is available."""
    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return True

        result = subprocess.run(  # pragma: no cover
            ["docker-compose", "version"],
            capture_output=True,
            text=True,
            check=False,
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
        check=False,
    )
    if result.returncode == 0:
        return ["docker", "compose"]
    return ["docker-compose"]  # pragma: no cover


def _copy_stack_file(
    config_file, dest, app_url=None, stack_log_dir: Path | None = None
):
    """Copy a single stack config file, substituting placeholders if needed."""
    # For alloy-config.alloy, substitute the metrics scrape URL
    if config_file.name == "alloy-config.alloy" and app_url:  # pragma: no cover
        content = config_file.read_text()
        content = content.replace('"host.docker.internal:8000"', f'"{app_url}"')
        dest.write_text(content)
    elif config_file.name == "docker-compose.yml":
        content = config_file.read_text()
        content = _render_stack_compose(content, stack_log_dir)
        dest.write_text(content)
    else:
        shutil.copy(config_file, dest)


def _get_stack_dir() -> Path:
    """Return the stack working directory without modifying any files."""
    work_dir = _resolve_stack_dir()
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir


def _get_work_dir(app_url=None):
    """Get or create working directory and copy stack configs."""
    work_dir = _resolve_stack_dir()
    work_dir.mkdir(parents=True, exist_ok=True)
    stack_log_dir: Path | None = None
    if _is_file_logging_enabled():
        stack_log_dir = _prepare_stack_log_dir(_resolve_stack_log_dir())

    # Copy stack files from package to work directory
    try:
        stack_path = (
            Path(__file__).parent.parent.parent / "management" / "commands" / "stack"
        )

        if stack_path.exists():
            for config_file in stack_path.glob("*"):
                if config_file.is_file():
                    dest = work_dir / config_file.name
                    _copy_stack_file(config_file, dest, app_url, stack_log_dir)
    except Exception as e:  # pragma: no cover
        click.secho(f"Warning: Could not copy stack files: {e}", fg="yellow")

    # Conditionally add celery-exporter when Celery is enabled and broker is configured
    if _is_celery_enabled():
        broker_url = _get_broker_url()
        if broker_url:
            valid, reason = _validate_exporter_broker_url(broker_url)
            if valid:
                container_broker_url = _rewrite_broker_url_for_container(broker_url)
                _write_celery_exporter_override(work_dir, container_broker_url)
                click.echo(f"  celery-exporter: broker {container_broker_url}")
            else:
                click.secho(
                    "  celery-exporter disabled: broker URL is not "
                    f"container-compatible ({reason}).",
                    fg="yellow",
                )
                click.echo(
                    "  Set DJANGO_SETTINGS_MODULE to your dev/prod settings "
                    "(for example tests.config.settings.local) before running "
                    "`manage.py o11y stack start`."
                )
                override = work_dir / CELERY_EXPORTER_COMPOSE_FILE
                if override.exists():
                    override.unlink()
        else:
            # Remove stale override if broker is no longer configured
            override = work_dir / CELERY_EXPORTER_COMPOSE_FILE
            if override.exists():
                override.unlink()

    return work_dir


def _is_file_logging_enabled() -> bool:
    """Return whether host file logging is enabled in effective config."""
    try:
        from django_o11y.config.setup import get_config

        config = get_config()
        return bool(config.get("LOGGING", {}).get("FILE_ENABLED", False))
    except Exception:  # pragma: no cover  # pylint: disable=broad-exception-caught
        return False


def _render_stack_compose(content: str, stack_log_dir: Path | None) -> str:
    """Render docker-compose.yml, conditionally injecting file-log bind mount."""
    start_marker = "__DJANGO_O11Y_STACK_LOG_MOUNT_START__"
    end_marker = "__DJANGO_O11Y_STACK_LOG_MOUNT_END__"

    if stack_log_dir is None:
        lines = content.splitlines()
        rendered: list[str] = []
        skip = False
        for line in lines:
            if start_marker in line:
                skip = True
                continue
            if end_marker in line:
                skip = False
                continue
            if not skip:
                rendered.append(line)
        return "\n".join(rendered) + "\n"

    content = content.replace(start_marker, "")
    content = content.replace(end_marker, "")
    return content.replace("__DJANGO_O11Y_STACK_LOG_DIR__", str(stack_log_dir))


def _prepare_stack_log_dir(stack_log_dir: Path) -> Path:
    """Ensure stack log dir exists and is writable by the current user.

    Docker bind mounts may create missing host directories as root. To avoid
    ownership drift, we pre-create the directory before docker compose runs.

    If the target exists but is not writable, fall back to ``/tmp/django-o11y``
    with a warning so stack startup can still proceed.
    """
    # Fast path: if the directory already exists and is writable, avoid
    # touching the filesystem hierarchy further.
    if os.access(stack_log_dir, os.W_OK):
        return stack_log_dir

    try:
        stack_log_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        return _fallback_stack_log_dir(stack_log_dir)

    if not os.access(stack_log_dir, os.W_OK):
        return _fallback_stack_log_dir(stack_log_dir)

    return stack_log_dir


def _fallback_stack_log_dir(original: Path) -> Path:
    """Return a writable fallback stack log dir and emit a warning."""
    fallback = Path("/tmp/django-o11y")
    fallback.mkdir(parents=True, exist_ok=True)
    click.secho(
        "Warning: stack log dir is not writable "
        f"({original}). Falling back to {fallback}.",
        fg="yellow",
    )
    click.echo(
        "Set DJANGO_O11Y_STACK_LOG_DIR and DJANGO_O11Y_LOGGING_FILE_PATH to a "
        "writable path to avoid this warning."
    )
    return fallback


def _resolve_stack_dir() -> Path:
    """Resolve stack directory using explicit env var, then XDG state dir."""
    if configured := os.environ.get("DJANGO_O11Y_STACK_DIR"):
        return Path(configured).expanduser()

    xdg_state_home = os.environ.get("XDG_STATE_HOME")
    if xdg_state_home:
        return Path(xdg_state_home).expanduser() / "django-o11y"

    return Path.home() / ".local" / "state" / "django-o11y"


def _resolve_stack_log_dir() -> Path:
    """Resolve host log dir to mount into the Alloy container.

    Explicit override via DJANGO_O11Y_STACK_LOG_DIR takes precedence,
    which is useful when log files land in a Docker volume mount that
    differs from the path Django would derive from its config.
    """
    if override := os.environ.get("DJANGO_O11Y_STACK_LOG_DIR"):
        return Path(override).expanduser()

    try:
        from django_o11y.config.setup import get_config

        config = get_config()
        file_path = config.get("LOGGING", {}).get("FILE_PATH")
        if file_path:
            return Path(file_path).expanduser().parent
    except Exception:  # pragma: no cover  # pylint: disable=broad-exception-caught
        pass

    return Path("/tmp/django-o11y")


def _print_service_urls(work_dir: Path | None = None):
    """Print URLs for accessing services."""
    click.echo("  Grafana:          http://localhost:3000")
    click.echo("  Prometheus:       http://localhost:9090")
    click.echo("  Tempo:            http://localhost:3200")
    click.echo("  Loki:             http://localhost:3100")
    click.echo("  Pyroscope:        http://localhost:4040")
    click.echo("  Alloy:            http://localhost:12345")
    if work_dir and (work_dir / CELERY_EXPORTER_COMPOSE_FILE).exists():
        click.echo(f"  celery-exporter:  http://localhost:{CELERY_EXPORTER_PORT}")


def _check_configuration():
    """Check configuration is loaded correctly."""
    ok, warn, err = 0, 0, 0

    try:
        from django_o11y.config.setup import get_o11y_config

        config = get_o11y_config()

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
        from django_o11y.config.setup import get_o11y_config

        config = get_o11y_config()

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


def _check_metrics_endpoint():
    """Check that the configured metrics endpoint is routed correctly."""
    ok, warn, err = 0, 0, 0

    try:
        from django_o11y.config.setup import get_o11y_config

        config = get_o11y_config()
        metrics_config = config.get("METRICS", {})

        if not metrics_config.get("PROMETHEUS_ENABLED", True):
            click.secho("  ⚠️  Metrics disabled", fg="yellow")
            warn += 1
            return ok, warn, err

        endpoint = metrics_config.get("PROMETHEUS_ENDPOINT", "/metrics")
        endpoint_path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        click.echo(f"  Endpoint: {endpoint_path}")

        try:
            match = resolve(endpoint_path)
        except Resolver404:
            click.secho(
                "  ❌ Endpoint not routed\n"
                "     Add `urlpatterns = [...] + get_urls()` in your root urls.py",
                fg="red",
            )
            err += 1
            return ok, warn, err

        from django_prometheus.exports import ExportToDjangoView

        if match.func is ExportToDjangoView:
            click.secho(
                "  ✅ Route exists and points to Prometheus exporter", fg="green"
            )
            ok += 1
        else:
            click.secho(
                "  ❌ Endpoint is routed to a different view\n"
                f"     Resolved view: {match.view_name or match.func.__name__}",
                fg="red",
            )
            err += 1

    except Exception as e:  # pragma: no cover
        click.secho(f"  ❌ Metrics route check failed: {e}", fg="red")
        err += 1

    return ok, warn, err


def _check_packages():
    """Check installed packages."""
    import importlib

    ok, warn, err = 0, 0, 0

    packages = [
        ("opentelemetry", "opentelemetry-api", "Core tracing"),
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

                from django_o11y.config.setup import get_o11y_config

                config = get_o11y_config()
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
