"""Tracing middleware for Django requests."""

from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


class TracingMiddleware:
    """
    Middleware that creates a span for each HTTP request.

    This is supplementary to the automatic Django instrumentation,
    providing additional control and customization.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        self.tracer = trace.get_tracer(__name__)

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

        try:
            response = self.get_response(request)

            if span.is_recording():
                span.set_attribute("http.status_code", response.status_code)
                if response.status_code >= 500:
                    span.set_status(Status(StatusCode.ERROR))

            return response

        except Exception as exc:
            if span.is_recording():
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
