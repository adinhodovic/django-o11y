"""Logging middleware that extends django-structlog with OpenTelemetry integration."""

from typing import Callable

from django.http import HttpRequest, HttpResponse
from django_structlog.middlewares import (
    RequestMiddleware as DjangoStructlogRequestMiddleware,
)
from opentelemetry import trace


class LoggingMiddleware(DjangoStructlogRequestMiddleware):
    """
    Wraps django-structlog's RequestMiddleware and copies request_id onto the active OTel span.

    All django-structlog behaviour (request_id, correlation_id, user_id logging, etc.) is
    inherited unchanged. The only addition is setting the ``request.id`` span attribute so
    traces and logs share the same identifier.
    """

    def __call__(self, request: HttpRequest) -> HttpResponse:
        import uuid

        request_id = (
            request.headers.get("X-Request-ID")
            or request.META.get("HTTP_X_REQUEST_ID")
            or str(uuid.uuid4())
        )

        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("request.id", request_id)

        return super().__call__(request)
