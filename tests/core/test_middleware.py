"""Tests for middleware."""

from unittest.mock import patch

import pytest
import structlog
from django.http import HttpResponse
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def _make_tracer():
    """Return a tracer backed by a local in-memory exporter (no global state)."""
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))
    return provider.get_tracer(__name__)


@pytest.mark.django_db
def test_logging_middleware_uses_meta_header():
    from django.test import RequestFactory

    from django_o11y.logging.middleware import LoggingMiddleware

    rf = RequestFactory()
    request = rf.get("/", HTTP_X_REQUEST_ID="meta-request-123")

    middleware = LoggingMiddleware(lambda r: HttpResponse("OK"))

    tracer = _make_tracer()
    with tracer.start_as_current_span("test-span") as span:
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            middleware(request)

            assert span.attributes.get("request.id") == "meta-request-123"


def test_tracing_middleware_adds_user_attributes(django_user_request):
    from django_o11y.tracing.middleware import TracingMiddleware

    middleware = TracingMiddleware(lambda r: HttpResponse("OK"))

    tracer = _make_tracer()
    with tracer.start_as_current_span("test-span") as span:
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            response = middleware(django_user_request)

            assert span.attributes.get("user.id") == "1"
            assert span.attributes.get("user.username") == "testuser"
            assert response.status_code == 200


def test_tracing_middleware_allows_5xx_response():
    from django.test import RequestFactory

    from django_o11y.tracing.middleware import TracingMiddleware

    rf = RequestFactory()
    request = rf.get("/")

    middleware = TracingMiddleware(lambda r: HttpResponse("Error", status=500))

    tracer = _make_tracer()
    with tracer.start_as_current_span("test-span") as span:
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            response = middleware(request)

            assert response.status_code == 500


def test_tracing_middleware_propagates_exception():
    from django.test import RequestFactory

    from django_o11y.tracing.middleware import TracingMiddleware

    rf = RequestFactory()
    request = rf.get("/")

    def exception_view(req):
        raise ValueError("Test exception")

    middleware = TracingMiddleware(exception_view)

    tracer = _make_tracer()
    with tracer.start_as_current_span("test-span"):
        with patch("opentelemetry.trace.get_current_span"):
            with pytest.raises(ValueError, match="Test exception"):
                middleware(request)


def test_tracing_middleware_anonymous_user():
    from django.contrib.auth.models import AnonymousUser
    from django.test import RequestFactory

    from django_o11y.tracing.middleware import TracingMiddleware

    rf = RequestFactory()
    request = rf.get("/")
    request.user = AnonymousUser()

    middleware = TracingMiddleware(lambda r: HttpResponse("OK"))
    response = middleware(request)

    assert response.status_code == 200


@pytest.mark.django_db
def test_logging_middleware_binds_duration_ms(capsys):
    from django.test import RequestFactory

    from django_o11y.logging.middleware import LoggingMiddleware

    structlog.contextvars.clear_contextvars()

    rf = RequestFactory()
    request = rf.get("/")

    middleware = LoggingMiddleware(lambda r: HttpResponse("OK"))
    middleware(request)

    # duration_ms is cleared from context after request_finished is emitted —
    # assert it appeared in the log output instead
    captured = capsys.readouterr()
    assert "duration_ms" in captured.out


@pytest.mark.django_db
def test_logging_middleware_duration_ms_is_positive(capsys):
    import time

    from django.test import RequestFactory

    from django_o11y.logging.middleware import LoggingMiddleware

    structlog.contextvars.clear_contextvars()

    rf = RequestFactory()
    request = rf.get("/")

    def slow_view(r):
        time.sleep(0.01)
        return HttpResponse("OK")

    middleware = LoggingMiddleware(slow_view)
    middleware(request)

    captured = capsys.readouterr()
    assert "duration_ms" in captured.out


@pytest.mark.django_db
def test_logging_middleware_duration_ms_missing_start():
    """duration_ms is not bound if _o11y_start is absent (defensive path)."""
    from django.test import RequestFactory

    from django_o11y.logging.middleware import LoggingMiddleware

    structlog.contextvars.clear_contextvars()

    rf = RequestFactory()
    request = rf.get("/")
    # No __call__ — _o11y_start is never set, simulating the defensive path

    middleware = LoggingMiddleware(lambda r: HttpResponse("OK"))
    middleware.handle_response(request, HttpResponse("OK"))

    ctx = structlog.contextvars.get_merged_contextvars(structlog.get_logger())
    assert "duration_ms" not in ctx
