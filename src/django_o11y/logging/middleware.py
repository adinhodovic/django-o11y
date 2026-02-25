"""Logging middleware that extends django-structlog with OpenTelemetry integration."""

import uuid
from typing import Any

from django.http import HttpRequest
from django_structlog.middlewares import (
    RequestMiddleware as DjangoStructlogRequestMiddleware,
)
from opentelemetry import trace


class LoggingMiddleware(DjangoStructlogRequestMiddleware):
    """
    Extends django-structlog's RequestMiddleware with OTel span integration.

    All django-structlog behaviour (request_id, correlation_id, user_id, etc.) is
    inherited unchanged. The only addition is setting the ``request.id`` span
    attribute so traces and logs share the same identifier.
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
