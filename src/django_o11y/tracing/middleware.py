"""Tracing middleware for Django requests."""

from collections.abc import Callable
from inspect import iscoroutinefunction, markcoroutinefunction

from django.http import HttpRequest, HttpResponse
from opentelemetry import trace
from opentelemetry.propagate import extract
from opentelemetry.trace import SpanKind

from django_o11y.tracing.utils import get_tracer


class TracingMiddleware:
    """Annotates the active span with request metadata.

    In WSGI mode, DjangoInstrumentor owns the server span. This middleware
    annotates it with route and user attributes.

    In ASGI mode, DjangoInstrumentor activates its span inside a
    sync_to_async thread. ContextVar changes in that thread don't propagate
    back to the async event loop, so the span is invisible when
    django-structlog's handle_response fires. This middleware creates its own
    server span in the async context so trace_id/span_id appear on all
    request log lines.

    Works in WSGI and ASGI.
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
            attributes={"url.path": request.path, "http.request.method": method},
        ) as span:
            self._annotate_user(request, span)
            response = await self.get_response(request)  # type: ignore[misc]
            if span.is_recording():
                span.set_attribute("http.response.status_code", response.status_code)
            return response

    def _annotate_request(self, request: HttpRequest) -> None:
        span = trace.get_current_span()

        if span.is_recording():
            span.set_attribute("url.path", request.path)
            self._annotate_user(request, span)

    def _annotate_user(self, request: HttpRequest, span: trace.Span) -> None:
        if not span.is_recording():
            return
        if not hasattr(request, "user") or not request.user:  # type: ignore[union-attr]
            return
        user = request.user  # type: ignore[union-attr]
        is_auth = getattr(user, "is_authenticated", False)
        if callable(is_auth):
            try:
                is_auth = is_auth()
            except Exception:
                return
        if not is_auth:
            return
        span.set_attribute(
            "user.id", str(getattr(user, "pk", None) or getattr(user, "id", None))
        )
        span.set_attribute("user.username", user.username)  # type: ignore[union-attr]
