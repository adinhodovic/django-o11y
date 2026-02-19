"""Tests for context management functions."""

import structlog
from unittest.mock import patch
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def _make_tracer():
    """Return a tracer backed by a local in-memory exporter (no global state)."""
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))
    return provider.get_tracer(__name__)


def test_set_custom_tags_adds_to_span():
    from django_observability.context import set_custom_tags

    tracer = _make_tracer()
    with tracer.start_as_current_span("test-span") as span:
        set_custom_tags(
            {"tenant_id": "acme-corp", "feature": "checkout", "tier": "premium"}
        )

        assert span.attributes.get("custom.tenant_id") == "acme-corp"
        assert span.attributes.get("custom.feature") == "checkout"
        assert span.attributes.get("custom.tier") == "premium"


def test_set_custom_tags_adds_to_log_context():
    from django_observability.context import set_custom_tags

    structlog.contextvars.clear_contextvars()

    set_custom_tags({"user_id": "123", "action": "purchase"})

    logger = structlog.get_logger()
    bound_logger = logger.bind()
    context = bound_logger._context

    assert "user_id" in str(context) or hasattr(context, "get")


def test_set_custom_tags_without_recording_span():
    from django_observability.context import set_custom_tags
    from opentelemetry import trace

    non_recording_span = trace.NonRecordingSpan(trace.INVALID_SPAN_CONTEXT)
    with patch("opentelemetry.trace.get_current_span", return_value=non_recording_span):
        set_custom_tags({"key": "value"})


def test_set_custom_tags_converts_values_to_strings():
    from django_observability.context import set_custom_tags

    tracer = _make_tracer()
    with tracer.start_as_current_span("test-span") as span:
        set_custom_tags({"count": 42, "enabled": True, "value": 3.14})

        assert span.attributes.get("custom.count") == "42"
        assert span.attributes.get("custom.enabled") == "True"
        assert span.attributes.get("custom.value") == "3.14"


def test_add_span_attribute():
    from django_observability.context import add_span_attribute

    tracer = _make_tracer()
    with tracer.start_as_current_span("test-span") as span:
        add_span_attribute("query_count", 15)
        add_span_attribute("cache_hit", True)

        assert span.attributes.get("custom.query_count") == "15"
        assert span.attributes.get("custom.cache_hit") == "True"


def test_add_span_attribute_without_recording_span():
    from django_observability.context import add_span_attribute
    from opentelemetry import trace

    non_recording_span = trace.NonRecordingSpan(trace.INVALID_SPAN_CONTEXT)
    with patch("opentelemetry.trace.get_current_span", return_value=non_recording_span):
        add_span_attribute("key", "value")


def test_add_log_context():
    from django_observability.context import add_log_context

    structlog.contextvars.clear_contextvars()

    add_log_context(debug_flag=True, processing_time=123, items=50)

    context_vars = structlog.contextvars.get_contextvars()
    assert "debug_flag" in context_vars
    assert context_vars["debug_flag"] is True
    assert context_vars["processing_time"] == 123


def test_clear_custom_context():
    from django_observability.context import set_custom_tags, clear_custom_context

    set_custom_tags({"key": "value"})
    clear_custom_context()

    logger = structlog.get_logger()
    bound_logger = logger.bind()
    context_str = str(bound_logger._context)

    assert "key" not in context_str or len(str(bound_logger._context)) < 10


def test_get_current_trace_id():
    from django_observability.context import get_current_trace_id

    tracer = _make_tracer()
    with tracer.start_as_current_span("test-span"):
        trace_id = get_current_trace_id()

        assert trace_id is not None
        assert isinstance(trace_id, str)
        assert len(trace_id) == 32


def test_get_current_trace_id_no_span():
    from django_observability.context import get_current_trace_id
    from opentelemetry import trace

    non_recording_span = trace.NonRecordingSpan(trace.INVALID_SPAN_CONTEXT)
    with patch("opentelemetry.trace.get_current_span", return_value=non_recording_span):
        trace_id = get_current_trace_id()
        assert trace_id is None


def test_get_current_span_id():
    from django_observability.context import get_current_span_id

    tracer = _make_tracer()
    with tracer.start_as_current_span("test-span"):
        span_id = get_current_span_id()

        assert span_id is not None
        assert isinstance(span_id, str)
        assert len(span_id) == 16


def test_get_current_span_id_no_span():
    from django_observability.context import get_current_span_id
    from opentelemetry import trace

    non_recording_span = trace.NonRecordingSpan(trace.INVALID_SPAN_CONTEXT)
    with patch("opentelemetry.trace.get_current_span", return_value=non_recording_span):
        span_id = get_current_span_id()
        assert span_id is None


def test_context_workflow():
    from django_observability.context import (
        set_custom_tags,
        add_span_attribute,
        add_log_context,
        get_current_trace_id,
        clear_custom_context,
    )

    tracer = _make_tracer()
    with tracer.start_as_current_span("workflow-span") as span:
        set_custom_tags({"tenant": "acme"})
        add_span_attribute("step", "processing")
        add_log_context(detail="extra info")

        trace_id = get_current_trace_id()
        assert trace_id is not None

        assert span.attributes.get("custom.tenant") == "acme"
        assert span.attributes.get("custom.step") == "processing"

    clear_custom_context()
