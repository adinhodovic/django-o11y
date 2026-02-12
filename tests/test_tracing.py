"""Tests for tracing provider setup."""

import pytest
from unittest.mock import MagicMock, patch


def test_setup_tracing_creates_provider():
    from django_observability.tracing.provider import setup_tracing

    config = {
        "SERVICE_NAME": "test-service",
        "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
    }

    with patch("django_observability.tracing.provider.OTLPSpanExporter"):
        with patch("django_observability.tracing.provider.trace.set_tracer_provider"):
            provider = setup_tracing(config)

            assert provider is not None


def test_setup_tracing_with_namespace():
    from django_observability.tracing.provider import setup_tracing

    config = {
        "SERVICE_NAME": "test-service",
        "NAMESPACE": "production",
        "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
    }

    with patch("django_observability.tracing.provider.OTLPSpanExporter"):
        with patch("django_observability.tracing.provider.trace.set_tracer_provider"):
            provider = setup_tracing(config)

            assert provider is not None


def test_setup_tracing_without_namespace():
    from django_observability.tracing.provider import setup_tracing

    config = {
        "SERVICE_NAME": "test-service",
        "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
    }

    with patch("django_observability.tracing.provider.OTLPSpanExporter"):
        with patch("django_observability.tracing.provider.trace.set_tracer_provider"):
            provider = setup_tracing(config)

            assert provider is not None


def test_setup_tracing_with_resource_attributes():
    from django_observability.tracing.provider import setup_tracing

    config = {
        "SERVICE_NAME": "test-service",
        "RESOURCE_ATTRIBUTES": {"region": "us-west-2", "team": "backend"},
        "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
    }

    with patch("django_observability.tracing.provider.OTLPSpanExporter"):
        with patch("django_observability.tracing.provider.trace.set_tracer_provider"):
            provider = setup_tracing(config)

            assert provider is not None


def test_setup_tracing_without_resource_attributes():
    from django_observability.tracing.provider import setup_tracing

    config = {
        "SERVICE_NAME": "test-service",
        "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
    }

    with patch("django_observability.tracing.provider.OTLPSpanExporter"):
        with patch("django_observability.tracing.provider.trace.set_tracer_provider"):
            provider = setup_tracing(config)

            assert provider is not None


def test_setup_tracing_without_otlp_endpoint():
    from django_observability.tracing.provider import setup_tracing

    config = {
        "SERVICE_NAME": "test-service",
        "TRACING": {"OTLP_ENDPOINT": None},
    }

    with patch("django_observability.tracing.provider.trace.set_tracer_provider"):
        provider = setup_tracing(config)

        assert provider is not None


def test_setup_tracing_with_console_exporter():
    from django_observability.tracing.provider import setup_tracing

    config = {
        "SERVICE_NAME": "test-service",
        "TRACING": {
            "OTLP_ENDPOINT": "http://localhost:4317",
            "CONSOLE_EXPORTER": True,
        },
    }

    with patch("django_observability.tracing.provider.OTLPSpanExporter"):
        with patch(
            "django_observability.tracing.provider.ConsoleSpanExporter"
        ) as mock_console:
            with patch(
                "django_observability.tracing.provider.trace.set_tracer_provider"
            ):
                mock_console.return_value = MagicMock()

                provider = setup_tracing(config)

                assert provider is not None
                mock_console.assert_called_once()


def test_setup_tracing_without_console_exporter():
    from django_observability.tracing.provider import setup_tracing

    config = {
        "SERVICE_NAME": "test-service",
        "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
    }

    with patch("django_observability.tracing.provider.OTLPSpanExporter"):
        with patch(
            "django_observability.tracing.provider.ConsoleSpanExporter"
        ) as mock_console:
            with patch(
                "django_observability.tracing.provider.trace.set_tracer_provider"
            ):
                provider = setup_tracing(config)

                assert provider is not None
                mock_console.assert_not_called()


def test_get_tracer():
    from django_observability.tracing.provider import get_tracer

    with patch("django_observability.tracing.provider.trace.get_tracer") as mock_get:
        mock_get.return_value = MagicMock()

        tracer = get_tracer("test-module")

        mock_get.assert_called_once_with("test-module")
        assert tracer is not None


def test_get_tracer_default_name():
    from django_observability.tracing.provider import get_tracer

    with patch("django_observability.tracing.provider.trace.get_tracer") as mock_get:
        mock_get.return_value = MagicMock()

        tracer = get_tracer()

        mock_get.assert_called_once_with("django_observability")
        assert tracer is not None


def test_setup_tracing_sets_global_provider():
    from django_observability.tracing.provider import setup_tracing

    config = {
        "SERVICE_NAME": "test-service",
        "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317"},
    }

    with patch("django_observability.tracing.provider.OTLPSpanExporter"):
        with patch(
            "django_observability.tracing.provider.trace.set_tracer_provider"
        ) as mock_set:
            provider = setup_tracing(config)

            mock_set.assert_called_once()
            assert provider is not None
