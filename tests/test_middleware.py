"""Tests for middleware."""

import pytest
from unittest.mock import patch
from django.http import HttpResponse
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode


def _make_tracer():
    """Return a tracer backed by a local in-memory exporter (no global state)."""
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))
    return provider.get_tracer(__name__)


@pytest.mark.django_db
def test_logging_middleware_uses_meta_header():
    from django_observability.middleware.logging import LoggingMiddleware
    from django.test import RequestFactory

    rf = RequestFactory()
    request = rf.get("/", HTTP_X_REQUEST_ID="meta-request-123")

    middleware = LoggingMiddleware(lambda r: HttpResponse("OK"))

    tracer = _make_tracer()
    with tracer.start_as_current_span("test-span") as span:
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            middleware(request)

            assert span.attributes.get("request.id") == "meta-request-123"


def test_tracing_middleware_adds_user_attributes(django_user_request):
    from django_observability.middleware.tracing import TracingMiddleware

    middleware = TracingMiddleware(lambda r: HttpResponse("OK"))

    tracer = _make_tracer()
    with tracer.start_as_current_span("test-span") as span:
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            response = middleware(django_user_request)

            assert span.attributes.get("user.id") == "1"
            assert span.attributes.get("user.username") == "testuser"
            assert response.status_code == 200


def test_tracing_middleware_5xx_error_status():
    from django_observability.middleware.tracing import TracingMiddleware
    from django.test import RequestFactory

    rf = RequestFactory()
    request = rf.get("/")

    middleware = TracingMiddleware(lambda r: HttpResponse("Error", status=500))

    tracer = _make_tracer()
    with tracer.start_as_current_span("test-span") as span:
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            response = middleware(request)

            assert response.status_code == 500
            assert span.status.status_code == StatusCode.ERROR


def test_tracing_middleware_records_exception():
    from django_observability.middleware.tracing import TracingMiddleware
    from django.test import RequestFactory

    rf = RequestFactory()
    request = rf.get("/")

    def exception_view(req):
        raise ValueError("Test exception")

    middleware = TracingMiddleware(exception_view)

    tracer = _make_tracer()
    with tracer.start_as_current_span("test-span") as span:
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            with pytest.raises(ValueError, match="Test exception"):
                middleware(request)

            assert span.status.status_code == StatusCode.ERROR


def test_tracing_middleware_anonymous_user():
    from django_observability.middleware.tracing import TracingMiddleware
    from django.test import RequestFactory
    from django.contrib.auth.models import AnonymousUser

    rf = RequestFactory()
    request = rf.get("/")
    request.user = AnonymousUser()

    middleware = TracingMiddleware(lambda r: HttpResponse("OK"))
    response = middleware(request)

    assert response.status_code == 200
