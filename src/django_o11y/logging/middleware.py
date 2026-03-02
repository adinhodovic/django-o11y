"""Logging middleware that adds OpenTelemetry integration to django-structlog."""

import uuid
from typing import Any

from django.http import HttpRequest
from django_structlog.middlewares import (
    RequestMiddleware as DjangoStructlogRequestMiddleware,
)
from opentelemetry import trace


class LoggingMiddleware(DjangoStructlogRequestMiddleware):
    """Extend django-structlog request middleware with OTel span context.

    This keeps all existing django-structlog behavior and adds ``request.id``
    to the active span so traces and logs share the same request identifier.
    """

    def __call__(self, request: HttpRequest) -> Any:
        request_id = (
            request.headers.get("X-Request-ID")
            or request.META.get("HTTP_X_REQUEST_ID")
            or str(uuid.uuid4())
        )

        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("request.id", request_id)

        return super().__call__(request)
