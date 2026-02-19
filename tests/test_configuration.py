"""Tests for configuration."""

from unittest.mock import patch

from django.conf import settings


def test_config_loaded():
    assert hasattr(settings, "DJANGO_O11Y")
    assert settings.DJANGO_O11Y["SERVICE_NAME"] == "test-service"


def test_get_o11y_config():
    from django_o11y.conf import get_o11y_config

    config = get_o11y_config()

    assert config is not None
    assert "SERVICE_NAME" in config
    assert "TRACING" in config
    assert "LOGGING" in config
    assert "METRICS" in config


def test_config_defaults():
    from django_o11y.conf import get_o11y_config

    config = get_o11y_config()

    assert config["TRACING"]["ENABLED"] is True
    assert config["TRACING"]["SAMPLE_RATE"] == 1.0
    assert config["LOGGING"]["ENABLED"] is True
    assert config["LOGGING"]["LEVEL"] == "WARNING"


# ---------------------------------------------------------------------------
# logging/config.py — json format and OTLP paths
# ---------------------------------------------------------------------------


def test_build_logging_dict_json_format():
    from django_o11y.logging.config import build_logging_dict

    logging_config = {
        "FORMAT": "json",
        "LEVEL": "INFO",
        "REQUEST_LEVEL": "INFO",
        "DATABASE_LEVEL": "WARNING",
        "CELERY_LEVEL": "INFO",
        "COLORIZED": False,
        "OTLP_ENABLED": False,
    }

    result = build_logging_dict(logging_config)
    assert result["version"] == 1
    assert "json" in result["formatters"]


def test_build_logging_dict_with_otlp_enabled():
    from django_o11y.logging.config import build_logging_dict

    logging_config = {
        "FORMAT": "console",
        "LEVEL": "INFO",
        "REQUEST_LEVEL": "INFO",
        "DATABASE_LEVEL": "WARNING",
        "CELERY_LEVEL": "INFO",
        "COLORIZED": False,
        "OTLP_ENABLED": True,
        "OTLP_ENDPOINT": "http://localhost:4317",
    }

    with (
        patch("django_o11y.logging.otlp_handler.OTLPLogExporter"),
        patch("django_o11y.logging.otlp_handler.set_logger_provider"),
    ):
        result = build_logging_dict(logging_config)
        assert "otlp" in result["handlers"]


# ---------------------------------------------------------------------------
# logging/processors.py — parent span branch
# ---------------------------------------------------------------------------


def test_add_open_telemetry_spans_with_parent():
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from django_o11y.logging.processors import add_open_telemetry_spans

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))
    tracer = provider.get_tracer(__name__)

    with tracer.start_as_current_span("parent-span"):
        with tracer.start_as_current_span("child-span"):
            event_dict = {}
            result = add_open_telemetry_spans(None, None, event_dict)
            # Child span has a parent — parent_span_id should be present (line 36)
            assert "parent_span_id" in result
            assert "trace_id" in result
            assert "span_id" in result
