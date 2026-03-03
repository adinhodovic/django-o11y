"""Tests for logging configuration."""

import logging
import sys
from unittest.mock import MagicMock, patch

import pytest
import structlog

from django_o11y.logging.setup import DevEventFilter, build_logging_dict


def _base_config(**overrides):
    """Return a minimal logging config dict with sane defaults."""
    return {
        "FORMAT": "console",
        "LEVEL": "INFO",
        "REQUEST_LEVEL": "INFO",
        "DATABASE_LEVEL": "WARNING",
        "CELERY_LEVEL": "INFO",
        "COLORIZED": False,
        "OTLP_ENABLED": False,
        "FILE_ENABLED": False,
        **overrides,
    }


def test_build_logging_dict_json_format():
    result = build_logging_dict(
        {
            "FORMAT": "json",
            "LEVEL": "INFO",
            "REQUEST_LEVEL": "INFO",
            "DATABASE_LEVEL": "WARNING",
            "CELERY_LEVEL": "INFO",
            "COLORIZED": False,
            "OTLP_ENABLED": False,
        }
    )

    assert result["version"] == 1
    assert "json" in result["formatters"]
    assert "foreign_pre_chain" in result["formatters"]["default"]
    assert "foreign_pre_chain" in result["formatters"]["json"]


def test_build_logging_dict_with_otlp_enabled():
    config = _base_config(
        FORMAT="console", OTLP_ENABLED=True, OTLP_ENDPOINT="http://localhost:4317"
    )

    with (
        patch("django_o11y.logging.utils.OTLPLogExporter"),
        patch("django_o11y.logging.utils.set_logger_provider"),
    ):
        result = build_logging_dict(config)

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
            result = add_open_telemetry_spans(None, None, {})
            assert "parent_span_id" in result
            assert "trace_id" in result
            assert "span_id" in result


@pytest.mark.parametrize(
    "rich_exceptions, sys_modules_patch, expected_renderer_type",
    [
        (False, {}, structlog.dev.ConsoleRenderer),
        (True, {"rich": None}, structlog.dev.ConsoleRenderer),
    ],
    ids=["disabled", "enabled_without_rich"],
)
def test_build_logging_dict_rich_exceptions(
    rich_exceptions, sys_modules_patch, expected_renderer_type
):
    config = _base_config(RICH_EXCEPTIONS=rich_exceptions)

    with patch.dict(sys.modules, sys_modules_patch):
        result = build_logging_dict(config)

    assert isinstance(
        result["formatters"]["default"]["processor"], expected_renderer_type
    )


def test_build_logging_dict_rich_exceptions_enabled_with_rich():
    """RICH_EXCEPTIONS=True with Rich present injects RichTracebackFormatter."""
    config = _base_config(RICH_EXCEPTIONS=True)

    with patch.dict("sys.modules", {"rich": MagicMock()}):
        result = build_logging_dict(config)

    renderer = result["formatters"]["default"]["processor"]
    assert isinstance(renderer, structlog.dev.ConsoleRenderer)
    assert renderer._exception_formatter is not None
    assert isinstance(
        renderer._exception_formatter, structlog.dev.RichTracebackFormatter
    )


def test_dev_event_filter_filters_configured_event():
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
    config = _base_config(
        RICH_EXCEPTIONS=False, DEV_FILTERED_EVENTS=["request_started"]
    )

    result = build_logging_dict(config)
    filters = result["handlers"]["console"].get("filters", [])

    assert len(filters) == 1
    assert isinstance(filters[0], DevEventFilter)


# ---------------------------------------------------------------------------
# build_logging_dict extra= deep-merge
# ---------------------------------------------------------------------------


def test_build_logging_dict_extra_adds_logger():
    config = _base_config()
    extra = {"loggers": {"myapp": {"level": "DEBUG"}}}

    result = build_logging_dict(config, extra=extra)

    assert "myapp" in result["loggers"]
    assert result["loggers"]["myapp"]["level"] == "DEBUG"
    # Pre-existing loggers must still be present
    assert "django_o11y" in result["loggers"]


def test_build_logging_dict_extra_overrides_root_level():
    config = _base_config()
    extra = {"root": {"level": "DEBUG"}}

    result = build_logging_dict(config, extra=extra)

    assert result["root"]["level"] == "DEBUG"


# ---------------------------------------------------------------------------
# FILE_ENABLED=True
# ---------------------------------------------------------------------------


def test_build_logging_dict_file_enabled_adds_file_handler(tmp_path):
    log_file = tmp_path / "django.log"
    config = _base_config(
        FILE_ENABLED=True,
        FILE_PATH=str(log_file),
    )

    result = build_logging_dict(config)

    assert "file" in result["handlers"]
    assert result["handlers"]["file"]["class"] == "logging.FileHandler"
    assert result["handlers"]["file"]["formatter"] == "json"
    assert "file" in result["root"]["handlers"]


def test_build_logging_dict_file_disabled_no_file_handler():
    config = _base_config(FILE_ENABLED=False)
    result = build_logging_dict(config)
    assert "file" not in result["handlers"]
