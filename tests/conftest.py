"""Shared pytest fixtures for django-o11y tests."""

import socket
import time

import pytest
from click.testing import CliRunner

# Ports that must all be open before integration tests run.
# Alloy (:4317) is listed last because it depends_on all other services.
_STACK_PORTS = [
    ("localhost", 3000, "Grafana"),
    ("localhost", 9090, "Prometheus"),
    ("localhost", 3200, "Tempo"),
    ("localhost", 3100, "Loki"),
    ("localhost", 4040, "Pyroscope"),
    ("localhost", 12345, "Alloy UI"),
    ("localhost", 4317, "Alloy OTLP"),
]


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if the TCP port accepts a connection."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except OSError:
        return False


def _wait_for_stack(timeout: int = 120) -> bool:
    """Poll all stack ports until they are all open or timeout is reached."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if all(_port_open(host, port) for host, port, _ in _STACK_PORTS):
            return True
        time.sleep(3)
    return False


@pytest.fixture(scope="session")
def observability_stack():
    """Start the observability stack and wait until all services are ready.

    Tears the stack down after the session completes.  Any test that needs
    the stack should declare ``observability_stack`` as a parameter (or rely
    on the ``pytestmark`` set at module level).
    """
    from django_o11y.management.commands.o11y import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["stack", "start"])

    if result.exit_code != 0:
        pytest.skip(
            f"Could not start observability stack (exit {result.exit_code}):\n"
            f"{result.output}"
        )

    ready = _wait_for_stack(timeout=120)
    if not ready:
        not_open = [
            f"{name} (:{port})"
            for host, port, name in _STACK_PORTS
            if not _port_open(host, port)
        ]
        runner.invoke(cli, ["stack", "stop"])
        pytest.skip(
            f"Observability stack did not become ready. Still waiting: {not_open}"
        )

    yield

    runner.invoke(cli, ["stack", "stop"])


def make_config(overrides: dict | None = None) -> dict:
    """Return a full config dict merged with the library defaults.

    Tests that call setup functions directly should use this instead of
    building minimal dicts, so that direct key access in the library code
    does not raise KeyError when a key is not explicitly set.
    """
    from django_o11y.config.setup import _deep_merge, get_config

    base = get_config()
    if overrides:
        return _deep_merge(base, overrides)
    return base


@pytest.fixture
def mock_config():
    """Standard test config with all features enabled."""
    return make_config(
        {
            "SERVICE_NAME": "test-service",
            "ENVIRONMENT": "test",
            "NAMESPACE": "test-namespace",
            "TRACING": {
                "ENABLED": True,
                "OTLP_ENDPOINT": "http://localhost:4317",
                "SAMPLE_RATE": 1.0,
                "CONSOLE_EXPORTER": False,
            },
            "LOGGING": {
                "FORMAT": "console",
                "COLORIZED": False,
                "RICH_EXCEPTIONS": False,
                "OTLP_ENABLED": False,
            },
            "METRICS": {
                "PROMETHEUS_ENABLED": True,
            },
            "CELERY": {
                "ENABLED": True,
            },
            "PROFILING": {
                "ENABLED": True,
                "PYROSCOPE_URL": "http://localhost:4040",
            },
            "RESOURCE_ATTRIBUTES": {},
        }
    )


@pytest.fixture
def celery_app():
    """Mock Celery app for testing."""
    try:
        from celery import Celery

        app = Celery("test-app", broker="memory://", backend="cache+memory://")
        app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
        return app
    except ImportError:
        return pytest.skip("Celery not installed")  # skip() raises Skipped


@pytest.fixture
def django_user_request(rf):
    """Request factory with authenticated user."""
    from django.contrib.auth import get_user_model

    User = get_user_model()

    request = rf.get("/")
    user = User(id=1, username="testuser", is_staff=False)
    user.pk = 1
    request.user = user

    return request


@pytest.fixture(autouse=True)
def reset_o11y_cache():
    """Reset the lru_cache on get_o11y_config for each test."""
    from django_o11y.config.setup import get_o11y_config

    get_o11y_config.cache_clear()
    yield
    get_o11y_config.cache_clear()


@pytest.fixture(autouse=True)
def mock_worker_metrics_server(mocker):
    """Prevent tests from binding a real port for the worker metrics server."""
    mocker.patch("django_o11y.tracing.setup.setup_worker_metrics")
    mocker.patch("django_o11y.tracing.setup.prepare_worker_metrics_dir")
