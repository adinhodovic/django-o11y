"""Tests for configuration."""

import sys
import logging
from unittest.mock import MagicMock, patch

import structlog
from django.conf import settings


def test_config_loaded():
    assert hasattr(settings, "DJANGO_O11Y")
    assert settings.DJANGO_O11Y["SERVICE_NAME"] == "test-service"


def test_get_o11y_config():
    from django_o11y.config.setup import get_o11y_config

    config = get_o11y_config()

    assert config is not None
    assert "SERVICE_NAME" in config
    assert "TRACING" in config
    assert "LOGGING" in config
    assert "METRICS" in config


def test_config_defaults():
    from django_o11y.config.setup import get_o11y_config

    config = get_o11y_config()
    expected_sample_rate = 1.0 if settings.DEBUG else 0.01

    assert config["TRACING"]["ENABLED"] is True
    assert config["TRACING"]["SAMPLE_RATE"] == expected_sample_rate
    assert config["LOGGING"]["LEVEL"] == "WARNING"


def test_build_logging_dict_json_format():
    from django_o11y.logging.setup import build_logging_dict

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
    assert "foreign_pre_chain" in result["formatters"]["default"]
    assert "foreign_pre_chain" in result["formatters"]["json"]


def test_build_logging_dict_with_otlp_enabled():
    from django_o11y.logging.setup import build_logging_dict

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
        patch("django_o11y.logging.utils.OTLPLogExporter"),
        patch("django_o11y.logging.utils.set_logger_provider"),
    ):
        result = build_logging_dict(logging_config)
        assert "otlp" in result["handlers"]


def test_add_open_telemetry_spans_with_parent():
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from django_o11y.logging.utils import add_open_telemetry_spans

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


def test_build_logging_dict_rich_exceptions_disabled():
    """RICH_EXCEPTIONS=False produces a valid ConsoleRenderer without error.

    When rich is installed structlog defaults to RichTracebackFormatter on its
    own — that's structlog's behaviour, not ours.  Our flag only controls
    whether we *explicitly* inject it; with False we leave the choice to
    structlog.  We just assert the call succeeds and returns a renderer.
    """
    from django_o11y.logging.setup import build_logging_dict

    logging_config = {
        "FORMAT": "console",
        "LEVEL": "INFO",
        "REQUEST_LEVEL": "INFO",
        "DATABASE_LEVEL": "WARNING",
        "CELERY_LEVEL": "INFO",
        "COLORIZED": False,
        "RICH_EXCEPTIONS": False,
        "OTLP_ENABLED": False,
        "FILE_ENABLED": False,
    }

    result = build_logging_dict(logging_config)
    formatter = result["formatters"]["default"]
    renderer = formatter["processor"]
    assert isinstance(renderer, structlog.dev.ConsoleRenderer)


def test_build_logging_dict_rich_exceptions_enabled_without_rich():
    """RICH_EXCEPTIONS=True with Rich absent falls back silently to plain renderer."""
    from django_o11y.logging.setup import build_logging_dict

    logging_config = {
        "FORMAT": "console",
        "LEVEL": "INFO",
        "REQUEST_LEVEL": "INFO",
        "DATABASE_LEVEL": "WARNING",
        "CELERY_LEVEL": "INFO",
        "COLORIZED": False,
        "RICH_EXCEPTIONS": True,
        "OTLP_ENABLED": False,
        "FILE_ENABLED": False,
    }

    # Pretend Rich is not installed
    with patch.dict(sys.modules, {"rich": None}):
        result = build_logging_dict(logging_config)

    # Should still produce a valid logging dict without raising
    assert result["version"] == 1
    assert "default" in result["formatters"]


def test_build_logging_dict_rich_exceptions_enabled_with_rich():
    """RICH_EXCEPTIONS=True with Rich present injects RichTracebackFormatter."""
    from django_o11y.logging.setup import build_logging_dict

    logging_config = {
        "FORMAT": "console",
        "LEVEL": "INFO",
        "REQUEST_LEVEL": "INFO",
        "DATABASE_LEVEL": "WARNING",
        "CELERY_LEVEL": "INFO",
        "COLORIZED": False,
        "RICH_EXCEPTIONS": True,
        "OTLP_ENABLED": False,
        "FILE_ENABLED": False,
    }

    mock_rich = MagicMock()
    with patch.dict("sys.modules", {"rich": mock_rich}):
        result = build_logging_dict(logging_config)

    renderer = result["formatters"]["default"]["processor"]
    # RichTracebackFormatter is injected as exception_formatter
    assert isinstance(renderer, structlog.dev.ConsoleRenderer)
    assert renderer._exception_formatter is not None
    assert isinstance(
        renderer._exception_formatter, structlog.dev.RichTracebackFormatter
    )


def test_dev_event_filter_filters_configured_event():
    from django_o11y.logging.setup import DevEventFilter

    event_filter = DevEventFilter(["request_started"])

    filtered = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg={"event": "request_started"},
        args=(),
        exc_info=None,
    )
    kept = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg={"event": "request_finished"},
        args=(),
        exc_info=None,
    )

    assert event_filter.filter(filtered) is False
    assert event_filter.filter(kept) is True


def test_build_logging_dict_applies_dev_event_filter_in_console_mode():
    from django_o11y.logging.setup import DevEventFilter, build_logging_dict

    logging_config = {
        "FORMAT": "console",
        "LEVEL": "INFO",
        "REQUEST_LEVEL": "INFO",
        "DATABASE_LEVEL": "WARNING",
        "CELERY_LEVEL": "INFO",
        "COLORIZED": False,
        "RICH_EXCEPTIONS": False,
        "OTLP_ENABLED": False,
        "FILE_ENABLED": False,
        "DEV_FILTERED_EVENTS": ["request_started"],
    }

    result = build_logging_dict(logging_config)
    filters = result["handlers"]["console"].get("filters", [])

    assert len(filters) == 1
    assert isinstance(filters[0], DevEventFilter)
