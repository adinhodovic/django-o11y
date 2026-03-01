"""Tracing middleware for Django requests."""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from opentelemetry import trace

from django_o11y.tracing.utils import get_tracer


class TracingMiddleware:
    """
    Middleware that enriches the current request span with extra attributes.

    Span creation and HTTP status/error mapping are handled by automatic Django
    instrumentation. This middleware adds route and authenticated user metadata.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        self.tracer = get_tracer()

    def __call__(self, request: HttpRequest) -> HttpResponse:
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

        return self.get_response(request)
