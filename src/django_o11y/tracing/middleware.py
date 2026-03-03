"""Tracing middleware for Django requests."""

import sys
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.trace import SpanKind

from django_o11y.tracing.utils import get_tracer

if sys.version_info >= (3, 12):
    from inspect import iscoroutinefunction, markcoroutinefunction
else:
    from asgiref.sync import iscoroutinefunction, markcoroutinefunction


class TracingMiddleware:
    """Add request metadata to the active span, and own the server span in ASGI mode.

    In WSGI mode, DjangoInstrumentor creates and owns the server span.
    TracingMiddleware annotates it with route and user attributes.

    In ASGI mode, DjangoInstrumentor's span is activated inside a sync_to_async
    thread and its ContextVar attachment does not survive back to the async event
    loop context. TracingMiddleware creates its own server span in the async context
    so it remains active for the full request lifecycle — including when
    django-structlog's handle_response fires — ensuring trace_id/span_id are
    injected into all request log lines.

    Supports both WSGI (sync) and ASGI (async) deployments.
    """

    sync_capable = True
    async_capable = True

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        self.tracer = get_tracer()
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if iscoroutinefunction(self):
            return self.__acall__(request)  # type: ignore[return-value]
        self._annotate_request(request)
        return self.get_response(request)

    async def __acall__(self, request: HttpRequest) -> HttpResponse:
        # In ASGI mode we own the server span so it stays active in the async
        # context for the entire request — including sync_to_async calls made by
        # downstream middleware (e.g. django-structlog's handle_response).
        carrier = {
            k.decode("latin-1"): v.decode("latin-1")
            for k, v in request.scope.get("headers", [])  # type: ignore[union-attr]
        }
        parent_context = extract(carrier)

        method = request.method or "GET"
        span_name = f"{method} {request.path}"
        with self.tracer.start_as_current_span(
            span_name,
            context=parent_context,
            kind=SpanKind.SERVER,
            attributes={"http.route": request.path, "http.method": method},
        ) as span:
            self._annotate_user(request, span)
            response = await self.get_response(request)  # type: ignore[misc]
            if span.is_recording():
                span.set_attribute("http.status_code", response.status_code)
            return response

    def _annotate_request(self, request: HttpRequest) -> None:
        span = trace.get_current_span()

        if span.is_recording():
            span.set_attribute("http.route", request.path)
            self._annotate_user(request, span)

    def _annotate_user(self, request: HttpRequest, span: trace.Span) -> None:
        if not span.is_recording():
            return
        if (
            hasattr(request, "user") and request.user and request.user.is_authenticated  # type: ignore[union-attr]
        ):
            span.set_attribute("user.id", str(request.user.id))  # type: ignore[union-attr]
            span.set_attribute("user.username", request.user.username)  # type: ignore[union-attr]
