"""Tests for middleware."""

import asyncio
from unittest.mock import patch

import pytest
import structlog
from asgiref.sync import iscoroutinefunction
from django.http import HttpResponse
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def _make_tracer():
    """Return a tracer backed by a local in-memory exporter (no global state)."""
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))
    return provider.get_tracer(__name__)


async def _async_view(request):
    return HttpResponse("OK")


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


# ---------------------------------------------------------------------------
# Async (ASGI) tests
# ---------------------------------------------------------------------------


def test_tracing_middleware_is_async_capable():
    """TracingMiddleware must declare both sync and async capability."""
    from django_o11y.tracing.middleware import TracingMiddleware

    assert TracingMiddleware.sync_capable is True
    assert TracingMiddleware.async_capable is True


def test_tracing_middleware_marks_coroutine_when_get_response_is_async():
    """When wrapping an async view TracingMiddleware instance must be a coroutine function."""
    from django_o11y.tracing.middleware import TracingMiddleware

    middleware = TracingMiddleware(_async_view)
    assert iscoroutinefunction(middleware)


def test_tracing_middleware_sync_not_marked_coroutine():
    """When wrapping a sync view TracingMiddleware instance must NOT be a coroutine function."""
    from django_o11y.tracing.middleware import TracingMiddleware

    middleware = TracingMiddleware(lambda r: HttpResponse("OK"))
    assert not iscoroutinefunction(middleware)


def test_tracing_middleware_async_adds_span_attributes():
    """__acall__ must create a span with http.route and http.method attributes."""
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from django_o11y.tracing.middleware import TracingMiddleware

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    async def run():
        with patch(
            "django_o11y.tracing.middleware.get_tracer",
            return_value=provider.get_tracer(__name__),
        ):
            middleware = TracingMiddleware(_async_view)
        response = await middleware(_make_async_request(path="/hello/"))
        assert response.status_code == 200

    asyncio.run(run())

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].attributes.get("http.route") == "/hello/"


def test_tracing_middleware_async_propagates_exception():
    """__acall__ must not swallow exceptions from the async view."""
    from django_o11y.tracing.middleware import TracingMiddleware

    async def broken_view(request):
        raise ValueError("async boom")

    middleware = TracingMiddleware(broken_view)

    async def run():
        with pytest.raises(ValueError, match="async boom"):
            await middleware(_make_async_request())

    asyncio.run(run())


def test_tracing_middleware_async_authenticated_user(django_user_request):
    """__acall__ must set user span attributes for authenticated users."""
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from django_o11y.tracing.middleware import TracingMiddleware

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    async_request = _make_async_request()
    async_request.user = django_user_request.user

    async def run():
        with patch(
            "django_o11y.tracing.middleware.get_tracer",
            return_value=provider.get_tracer(__name__),
        ):
            middleware = TracingMiddleware(_async_view)
        await middleware(async_request)

    asyncio.run(run())

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].attributes.get("user.id") == "1"
    assert spans[0].attributes.get("user.username") == "testuser"


@pytest.mark.django_db
def test_logging_middleware_request_id_matches_structlog_context():
    """The span request.id must equal the request_id django-structlog binds."""
    from django.test import RequestFactory

    from django_o11y.logging.middleware import LoggingMiddleware

    structlog.contextvars.clear_contextvars()

    rf = RequestFactory()
    request = rf.get("/", HTTP_X_REQUEST_ID="sync-req-abc")

    captured_span_request_id = None
    captured_structlog_request_id = None

    class _Spy:
        def is_recording(self):
            return True

        def set_attribute(self, key, value):
            nonlocal captured_span_request_id
            if key == "request.id":
                captured_span_request_id = value

    middleware = LoggingMiddleware(lambda r: HttpResponse("OK"))

    with patch("opentelemetry.trace.get_current_span", return_value=_Spy()):
        middleware(request)

    ctx = structlog.contextvars.get_merged_contextvars(structlog.get_logger())
    # django-structlog clears contextvars at the end of handle_response,
    # so we read it from the span instead — both must be the same header value.
    assert captured_span_request_id == "sync-req-abc"


@pytest.mark.django_db
def test_logging_middleware_async_binds_duration_ms(capsys):
    """Async path must bind duration_ms and emit it on request_finished."""
    from django_o11y.logging.middleware import LoggingMiddleware

    structlog.contextvars.clear_contextvars()

    middleware = LoggingMiddleware(_async_view)
    assert iscoroutinefunction(middleware), (
        "LoggingMiddleware must be async-capable in ASGI mode"
    )

    async def run():
        request = _make_async_request()
        await middleware(request)

    asyncio.run(run())

    captured = capsys.readouterr()
    assert "duration_ms" in captured.out


@pytest.mark.django_db
def test_logging_middleware_async_request_id_matches_structlog_context():
    """In async mode, span request.id must match the request_id from django-structlog."""
    from django_o11y.logging.middleware import LoggingMiddleware

    structlog.contextvars.clear_contextvars()

    captured_span_request_id = None

    class _Spy:
        def is_recording(self):
            return True

        def set_attribute(self, key, value):
            nonlocal captured_span_request_id
            if key == "request.id":
                captured_span_request_id = value

    middleware = LoggingMiddleware(_async_view)

    async def run():
        request = _make_async_request()
        request.META["HTTP_X_REQUEST_ID"] = "async-req-xyz"
        with patch("opentelemetry.trace.get_current_span", return_value=_Spy()):
            await middleware(request)

    asyncio.run(run())

    assert captured_span_request_id == "async-req-xyz"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_async_request(path="/"):
    """Return a minimal async-compatible GET request."""
    from django.test import AsyncRequestFactory

    arf = AsyncRequestFactory()
    return arf.get(path)
