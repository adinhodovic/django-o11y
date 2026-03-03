"""Tests for middleware."""

import asyncio
import time
from unittest.mock import patch

import pytest
import structlog
from asgiref.sync import iscoroutinefunction
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import AsyncRequestFactory, RequestFactory
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from django_o11y.logging.middleware import LoggingMiddleware
from django_o11y.tracing.middleware import TracingMiddleware


def _make_tracer():
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter()))
    return provider.get_tracer(__name__)


def _make_provider_and_exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


async def _async_view(request):
    return HttpResponse("OK")


def _make_async_request(path="/"):
    return AsyncRequestFactory().get(path)


class _SpanSpy:
    """Minimal span stub that captures set_attribute calls."""

    def __init__(self):
        self.attributes = {}

    def is_recording(self):
        return True

    def set_attribute(self, key, value):
        self.attributes[key] = value


# ---------------------------------------------------------------------------
# LoggingMiddleware — sync
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_logging_middleware_uses_meta_header():
    request = RequestFactory().get("/", HTTP_X_REQUEST_ID="meta-request-123")
    middleware = LoggingMiddleware(lambda r: HttpResponse("OK"))
    tracer = _make_tracer()

    with tracer.start_as_current_span("test-span") as span:
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            middleware(request)
            assert span.attributes.get("request.id") == "meta-request-123"


@pytest.mark.django_db
def test_logging_middleware_binds_duration_ms(capsys):
    structlog.contextvars.clear_contextvars()
    middleware = LoggingMiddleware(lambda r: HttpResponse("OK"))
    middleware(RequestFactory().get("/"))

    assert "duration_ms" in capsys.readouterr().out


@pytest.mark.django_db
def test_logging_middleware_duration_ms_is_measurable(capsys):
    structlog.contextvars.clear_contextvars()

    def slow_view(r):
        time.sleep(0.01)
        return HttpResponse("OK")

    middleware = LoggingMiddleware(slow_view)
    middleware(RequestFactory().get("/"))

    out = capsys.readouterr().out
    assert "duration_ms" in out
    # Extract the value and confirm it is greater than zero
    import re

    match = re.search(r"duration_ms=([0-9.]+)", out)
    assert match and float(match.group(1)) > 0


@pytest.mark.django_db
def test_logging_middleware_duration_ms_missing_start():
    """duration_ms is not bound if _o11y_start is absent (defensive path)."""
    structlog.contextvars.clear_contextvars()
    request = RequestFactory().get("/")
    middleware = LoggingMiddleware(lambda r: HttpResponse("OK"))
    middleware.handle_response(request, HttpResponse("OK"))

    ctx = structlog.contextvars.get_merged_contextvars(structlog.get_logger())
    assert "duration_ms" not in ctx


@pytest.mark.django_db
def test_logging_middleware_request_id_matches_structlog_context():
    """span request.id must equal the request_id django-structlog binds."""
    structlog.contextvars.clear_contextvars()
    request = RequestFactory().get("/", HTTP_X_REQUEST_ID="sync-req-abc")
    spy = _SpanSpy()
    middleware = LoggingMiddleware(lambda r: HttpResponse("OK"))

    with patch("opentelemetry.trace.get_current_span", return_value=spy):
        middleware(request)

    assert spy.attributes.get("request.id") == "sync-req-abc"


# ---------------------------------------------------------------------------
# LoggingMiddleware — async
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_logging_middleware_async_binds_duration_ms(capsys):
    """Async path must bind duration_ms and emit it on request_finished."""
    structlog.contextvars.clear_contextvars()
    middleware = LoggingMiddleware(_async_view)
    assert iscoroutinefunction(middleware), (
        "LoggingMiddleware must be async-capable in ASGI mode"
    )

    asyncio.run(middleware(_make_async_request()))

    assert "duration_ms" in capsys.readouterr().out


@pytest.mark.django_db
def test_logging_middleware_async_request_id_matches_structlog_context():
    """In async mode, span request.id must match request_id from django-structlog."""
    structlog.contextvars.clear_contextvars()
    spy = _SpanSpy()
    middleware = LoggingMiddleware(_async_view)

    async def run():
        request = _make_async_request()
        request.META["HTTP_X_REQUEST_ID"] = "async-req-xyz"
        with patch("opentelemetry.trace.get_current_span", return_value=spy):
            await middleware(request)

    asyncio.run(run())

    assert spy.attributes.get("request.id") == "async-req-xyz"


# ---------------------------------------------------------------------------
# TracingMiddleware — sync
# ---------------------------------------------------------------------------


def test_tracing_middleware_adds_user_attributes(django_user_request):
    middleware = TracingMiddleware(lambda r: HttpResponse("OK"))
    tracer = _make_tracer()

    with tracer.start_as_current_span("test-span") as span:
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            response = middleware(django_user_request)
            assert span.attributes.get("user.id") == "1"
            assert span.attributes.get("user.username") == "testuser"
            assert response.status_code == 200


def test_tracing_middleware_allows_5xx_response():
    request = RequestFactory().get("/")
    middleware = TracingMiddleware(lambda r: HttpResponse("Error", status=500))
    tracer = _make_tracer()

    with tracer.start_as_current_span("test-span") as span:
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            assert middleware(request).status_code == 500


def test_tracing_middleware_propagates_exception():
    request = RequestFactory().get("/")

    def exception_view(req):
        raise ValueError("Test exception")

    middleware = TracingMiddleware(exception_view)
    tracer = _make_tracer()

    with tracer.start_as_current_span("test-span"):
        with patch("opentelemetry.trace.get_current_span"):
            with pytest.raises(ValueError, match="Test exception"):
                middleware(request)


def test_tracing_middleware_anonymous_user():
    request = RequestFactory().get("/")
    request.user = AnonymousUser()
    middleware = TracingMiddleware(lambda r: HttpResponse("OK"))
    assert middleware(request).status_code == 200


# ---------------------------------------------------------------------------
# TracingMiddleware — async capabilities
# ---------------------------------------------------------------------------


def test_tracing_middleware_is_async_capable():
    assert TracingMiddleware.sync_capable is True
    assert TracingMiddleware.async_capable is True


@pytest.mark.parametrize(
    "inner, expected",
    [(_async_view, True), (lambda r: HttpResponse("OK"), False)],
    ids=["async_view", "sync_view"],
)
def test_tracing_middleware_coroutine_detection(inner, expected):
    assert iscoroutinefunction(TracingMiddleware(inner)) is expected


def test_tracing_middleware_async_adds_span_attributes():
    """__acall__ must create a span with http.route and http.method attributes."""
    provider, exporter = _make_provider_and_exporter()

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
    assert spans[0].attributes.get("url.path") == "/hello/"


def test_tracing_middleware_async_propagates_exception():
    """__acall__ must not swallow exceptions from the async view."""

    async def broken_view(request):
        raise ValueError("async boom")

    middleware = TracingMiddleware(broken_view)

    async def run():
        with pytest.raises(ValueError, match="async boom"):
            await middleware(_make_async_request())

    asyncio.run(run())


def test_tracing_middleware_async_authenticated_user(django_user_request):
    """__acall__ must set user span attributes for authenticated users."""
    provider, exporter = _make_provider_and_exporter()

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
