"""Tests for tracing provider setup."""

from unittest.mock import MagicMock, patch

import pytest
from opentelemetry.trace import ProxyTracerProvider

from tests.conftest import make_config


@pytest.fixture(autouse=True)
def _unconfigured_global_tracer_provider():
    """Default to an unconfigured OTel provider in setup_tracing tests."""
    with patch(
        "django_o11y.tracing.setup.trace.get_tracer_provider",
        return_value=ProxyTracerProvider(),
    ):
        yield


def test_setup_tracing_creates_provider():
    from django_o11y.tracing.setup import setup_tracing

    config = make_config(
        {
            "SERVICE_NAME": "test-service",
            "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
        }
    )

    with patch("django_o11y.tracing.setup.OTLPSpanExporter"):
        with patch("django_o11y.tracing.setup.trace.set_tracer_provider"):
            provider = setup_tracing(config)

            assert provider is not None


def test_setup_tracing_skips_override_when_provider_already_set():
    from django_o11y.tracing.setup import setup_tracing

    config = make_config(
        {
            "SERVICE_NAME": "test-service",
            "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
        }
    )

    existing_provider = MagicMock()
    with patch(
        "django_o11y.tracing.setup.trace.get_tracer_provider",
        return_value=existing_provider,
    ):
        with patch("django_o11y.tracing.setup.trace.set_tracer_provider") as set_tp:
            provider = setup_tracing(config)

            assert provider is existing_provider
            set_tp.assert_not_called()


def test_setup_tracing_with_namespace():
    from django_o11y.tracing.setup import setup_tracing

    config = make_config(
        {
            "SERVICE_NAME": "test-service",
            "NAMESPACE": "production",
            "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
        }
    )

    with patch("django_o11y.tracing.setup.OTLPSpanExporter"):
        with patch("django_o11y.tracing.setup.trace.set_tracer_provider"):
            provider = setup_tracing(config)

            assert provider is not None


def test_setup_tracing_with_resource_attributes():
    from django_o11y.tracing.setup import setup_tracing

    config = make_config(
        {
            "SERVICE_NAME": "test-service",
            "RESOURCE_ATTRIBUTES": {"region": "us-west-2", "team": "backend"},
            "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
        }
    )

    with patch("django_o11y.tracing.setup.OTLPSpanExporter"):
        with patch("django_o11y.tracing.setup.trace.set_tracer_provider"):
            provider = setup_tracing(config)

            assert provider is not None


def test_setup_tracing_without_otlp_endpoint():
    from django_o11y.tracing.setup import setup_tracing

    config = make_config(
        {"SERVICE_NAME": "test-service", "TRACING": {"OTLP_ENDPOINT": None}}
    )

    with patch("django_o11y.tracing.setup.trace.set_tracer_provider"):
        provider = setup_tracing(config)

        assert provider is not None


def test_setup_tracing_with_console_exporter():
    from django_o11y.tracing.setup import setup_tracing

    config = make_config(
        {
            "SERVICE_NAME": "test-service",
            "TRACING": {
                "OTLP_ENDPOINT": "http://localhost:4317",
                "CONSOLE_EXPORTER": True,
            },
        }
    )

    with patch("django_o11y.tracing.setup.OTLPSpanExporter"):
        with patch("django_o11y.tracing.setup.ConsoleSpanExporter") as mock_console:
            with patch("django_o11y.tracing.setup.trace.set_tracer_provider"):
                mock_console.return_value = MagicMock()

                provider = setup_tracing(config)

                assert provider is not None
                mock_console.assert_called_once()


def test_setup_tracing_without_console_exporter():
    from django_o11y.tracing.setup import setup_tracing

    config = make_config(
        {
            "SERVICE_NAME": "test-service",
            "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
        }
    )

    with patch("django_o11y.tracing.setup.OTLPSpanExporter"):
        with patch("django_o11y.tracing.setup.ConsoleSpanExporter") as mock_console:
            with patch("django_o11y.tracing.setup.trace.set_tracer_provider"):
                provider = setup_tracing(config)

                assert provider is not None
                mock_console.assert_not_called()


def test_setup_tracing_adds_pyroscope_processor_when_enabled():
    import sys

    from django_o11y.tracing.setup import setup_tracing

    config = make_config(
        {
            "SERVICE_NAME": "test-service",
            "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
            "PROFILING": {"ENABLED": True},
        }
    )

    mock_processor = MagicMock()
    mock_pyroscope_otel = MagicMock()
    mock_pyroscope_otel.PyroscopeSpanProcessor.return_value = mock_processor

    with patch("django_o11y.tracing.setup.OTLPSpanExporter"):
        with patch("django_o11y.tracing.setup.trace.set_tracer_provider"):
            with patch.dict(sys.modules, {"pyroscope.otel": mock_pyroscope_otel}):
                provider = setup_tracing(config)

                assert provider is not None
                mock_pyroscope_otel.PyroscopeSpanProcessor.assert_called_once()


def test_setup_tracing_skips_pyroscope_processor_when_unavailable():
    import sys

    from django_o11y.tracing.setup import setup_tracing

    config = make_config(
        {
            "SERVICE_NAME": "test-service",
            "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
            "PROFILING": {"ENABLED": True},
        }
    )

    with patch("django_o11y.tracing.setup.OTLPSpanExporter"):
        with patch("django_o11y.tracing.setup.trace.set_tracer_provider"):
            with patch.dict(sys.modules, {"pyroscope.otel": None}):
                provider = setup_tracing(config)

                assert provider is not None


def test_setup_tracing_adds_pyroscope_processor_in_celery_prefork_worker_child():
    import sys

    from django_o11y.tracing.setup import setup_tracing

    config = make_config(
        {
            "SERVICE_NAME": "test-service",
            "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
            "PROFILING": {"ENABLED": True},
        }
    )

    mock_processor = MagicMock()
    mock_pyroscope_otel = MagicMock()
    mock_pyroscope_otel.PyroscopeSpanProcessor.return_value = mock_processor

    with patch("django_o11y.tracing.setup.OTLPSpanExporter"):
        with patch("django_o11y.tracing.setup.trace.set_tracer_provider"):
            with patch(
                "django_o11y.tracing.setup.is_celery_fork_pool_worker",
                return_value=True,
            ):
                with patch.dict(sys.modules, {"pyroscope.otel": mock_pyroscope_otel}):
                    provider = setup_tracing(config)

                    assert provider is not None
                    mock_pyroscope_otel.PyroscopeSpanProcessor.assert_called_once()


def test_setup_tracing_skips_pyroscope_processor_in_celery_prefork_boot_process():
    import sys

    from django_o11y.tracing.setup import setup_tracing

    config = make_config(
        {
            "SERVICE_NAME": "test-service",
            "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
            "PROFILING": {"ENABLED": True},
        }
    )

    mock_pyroscope_otel = MagicMock()

    with patch("django_o11y.tracing.setup.OTLPSpanExporter"):
        with patch("django_o11y.tracing.setup.trace.set_tracer_provider"):
            with patch(
                "django_o11y.tracing.setup.is_celery_prefork_pool",
                return_value=True,
            ):
                with patch.dict(sys.modules, {"pyroscope.otel": mock_pyroscope_otel}):
                    provider = setup_tracing(config)

                    assert provider is not None
                    mock_pyroscope_otel.PyroscopeSpanProcessor.assert_not_called()
