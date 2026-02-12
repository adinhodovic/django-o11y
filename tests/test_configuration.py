"""Tests for configuration."""

import pytest
from django.conf import settings
from django.test import override_settings
from unittest.mock import patch, MagicMock


def test_config_loaded():
    assert hasattr(settings, "DJANGO_OBSERVABILITY")
    assert settings.DJANGO_OBSERVABILITY["SERVICE_NAME"] == "test-service"


def test_get_observability_config():
    from django_observability.conf import get_observability_config

    config = get_observability_config()

    assert config is not None
    assert "SERVICE_NAME" in config
    assert "TRACING" in config
    assert "LOGGING" in config
    assert "METRICS" in config


def test_config_defaults():
    from django_observability.conf import get_observability_config

    config = get_observability_config()

    assert config["TRACING"]["ENABLED"] is True
    assert config["TRACING"]["SAMPLE_RATE"] == 1.0
    assert config["LOGGING"]["ENABLED"] is True
    assert config["LOGGING"]["LEVEL"] == "WARNING"


# ---------------------------------------------------------------------------
# logging/config.py — json format and OTLP paths
# ---------------------------------------------------------------------------


def test_setup_logging_json_format():
    from django_observability.logging.config import setup_logging

    config = {
        "LOGGING": {
            "FORMAT": "json",
            "LEVEL": "INFO",
            "REQUEST_LEVEL": "INFO",
            "DATABASE_LEVEL": "WARNING",
            "CELERY_LEVEL": "INFO",
            "COLORIZED": False,
            "OTLP_ENABLED": False,
        }
    }

    # Drives the json branch (lines 52-55) and else formatter (line 79)
    setup_logging(config)


def test_setup_logging_with_otlp_enabled():
    from django_observability.logging.config import setup_logging

    config = {
        "LOGGING": {
            "FORMAT": "console",
            "LEVEL": "INFO",
            "REQUEST_LEVEL": "INFO",
            "DATABASE_LEVEL": "WARNING",
            "CELERY_LEVEL": "INFO",
            "COLORIZED": False,
            "OTLP_ENABLED": True,
            "OTLP_ENDPOINT": "http://localhost:4317",
        }
    }

    with (
        patch("django_observability.logging.otlp_handler.OTLPLogExporter"),
        patch("django_observability.logging.otlp_handler.set_logger_provider"),
    ):
        # Drives the OTLP_ENABLED branches (lines 95-105)
        setup_logging(config)


# ---------------------------------------------------------------------------
# logging/processors.py — parent span branch
# ---------------------------------------------------------------------------


def test_add_open_telemetry_spans_with_parent(mock_tracer):
    from django_observability.logging.processors import add_open_telemetry_spans
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )
    from opentelemetry import trace

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer(__name__)

    with tracer.start_as_current_span("parent-span"):
        with tracer.start_as_current_span("child-span"):
            event_dict = {}
            result = add_open_telemetry_spans(None, None, event_dict)
            # Child span has a parent — parent_span_id should be present (line 36)
            assert "parent_span_id" in result
            assert "trace_id" in result
            assert "span_id" in result
