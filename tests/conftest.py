"""Shared pytest fixtures for django-observability tests."""

import socket
import time

import pytest
from click.testing import CliRunner
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from unittest.mock import Mock, MagicMock, patch


# ---------------------------------------------------------------------------
# Integration fixture: full observability stack via Docker Compose
# ---------------------------------------------------------------------------

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
    from django_observability.management.commands.observability import cli

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


@pytest.fixture
def mock_config():
    """Standard test config with all features enabled."""
    return {
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
            "ENABLED": True,
            "FORMAT": "console",
            "LEVEL": "INFO",
            "COLORIZED": False,
            "RICH_EXCEPTIONS": False,
            "OTLP_ENABLED": False,
        },
        "METRICS": {
            "PROMETHEUS_ENABLED": True,
            "OTLP_ENABLED": False,
        },
        "CELERY": {
            "ENABLED": True,
        },
        "PROFILING": {
            "ENABLED": True,
            "PYROSCOPE_URL": "http://localhost:4040",
            "MODE": "push",
            "TAGS": {},
        },
        "RESOURCE_ATTRIBUTES": {},
        "CUSTOM_TAGS": {},
    }


@pytest.fixture
def mock_tracer():
    """Mock OpenTelemetry tracer with in-memory exporter."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = provider.get_tracer(__name__)

    # Store exporter for inspection in tests
    tracer._test_exporter = exporter

    yield tracer

    # Cleanup
    exporter.clear()


@pytest.fixture
def mock_span(mock_tracer):
    """Mock span for testing."""
    with mock_tracer.start_as_current_span("test-span") as span:
        yield span


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
        pytest.skip("Celery not installed")


@pytest.fixture
def django_user_request(rf):
    """Request factory with authenticated user."""
    from django.contrib.auth.models import User

    request = rf.get("/")
    user = User(id=1, username="testuser", is_staff=False)
    user.pk = 1
    request.user = user

    return request


@pytest.fixture
def django_anonymous_request(rf):
    """Request factory with anonymous user."""
    from django.contrib.auth.models import AnonymousUser

    request = rf.get("/")
    request.user = AnonymousUser()

    return request


@pytest.fixture
def mock_otlp_exporter():
    """Mock OTLP exporter to avoid network calls in tests."""
    with patch(
        "opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter"
    ) as mock:
        exporter = Mock()
        exporter.export.return_value = Mock(is_success=True)
        mock.return_value = exporter
        yield exporter


@pytest.fixture(autouse=True)
def reset_observability_cache():
    """Reset the lru_cache on get_observability_config for each test."""
    from django_observability.conf import get_observability_config

    get_observability_config.cache_clear()
    yield
    get_observability_config.cache_clear()


@pytest.fixture
def capture_structlog_output():
    """Capture structlog output for inspection in tests."""
    import structlog
    from io import StringIO

    output = StringIO()

    # Configure structlog with string output
    structlog.configure(
        processors=[
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=output),
        cache_logger_on_first_use=False,
    )

    yield output

    # Reset structlog config
    structlog.reset_defaults()


@pytest.fixture
def mock_django_settings(settings):
    """Provide easy access to Django settings for modification in tests."""
    return settings


@pytest.fixture
def django_user_model():
    """Provide Django User model for tests."""
    from django.contrib.auth import get_user_model

    return get_user_model()


@pytest.fixture
def clean_observability_state():
    """Reset observability state before and after tests."""
    from opentelemetry import trace
    from django_observability.conf import get_observability_config

    get_observability_config.cache_clear()

    yield

    get_observability_config.cache_clear()
