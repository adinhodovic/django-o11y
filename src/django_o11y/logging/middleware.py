"""Logging middleware that adds OpenTelemetry integration to django-structlog."""

import time
import uuid
from typing import Any

import structlog
from django.http import HttpRequest, HttpResponse
from django_structlog.middlewares import (
    RequestMiddleware as DjangoStructlogRequestMiddleware,
)
from opentelemetry import trace


class LoggingMiddleware(DjangoStructlogRequestMiddleware):
    """Extend django-structlog request middleware with OTel span context.

    This keeps all existing django-structlog behavior and adds ``request.id``
    to the active span so traces and logs share the same request identifier.
    It also binds ``duration_ms`` to the structlog context so it appears on
    both ``request_finished`` and ``request_failed`` log lines.
    """

    def __call__(self, request: HttpRequest) -> Any:
        request.META["_o11y_start"] = time.perf_counter()

        request_id = (
            request.headers.get("X-Request-ID")
            or request.META.get("HTTP_X_REQUEST_ID")
            or str(uuid.uuid4())
        )

        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("request.id", request_id)

        return super().__call__(request)

    def handle_response(self, request: HttpRequest, response: HttpResponse) -> None:
        start = request.META.get("_o11y_start")
        if start is not None:
            structlog.contextvars.bind_contextvars(
                duration_ms=round((time.perf_counter() - start) * 1000, 2)
            )
        super().handle_response(request, response)
