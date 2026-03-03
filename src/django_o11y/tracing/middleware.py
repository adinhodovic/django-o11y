"""Tracing middleware for Django requests."""

import sys
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from opentelemetry import trace

from django_o11y.tracing.utils import get_tracer

if sys.version_info >= (3, 12):
    from inspect import iscoroutinefunction, markcoroutinefunction
else:
    from asgiref.sync import iscoroutinefunction, markcoroutinefunction


class TracingMiddleware:
    """Add request metadata to the active request span.

    Django auto-instrumentation creates spans and handles status/error mapping.
    This middleware adds route and authenticated user fields.

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
        self._annotate_request(request)
        return await self.get_response(request)  # type: ignore[misc]

    def _annotate_request(self, request: HttpRequest) -> None:
        span = trace.get_current_span()

        if span.is_recording():
            span.set_attribute("http.route", request.path)

            if (
                hasattr(request, "user")
                and request.user
                and request.user.is_authenticated
            ):
                span.set_attribute("user.id", str(request.user.id))
                span.set_attribute("user.username", request.user.username)
