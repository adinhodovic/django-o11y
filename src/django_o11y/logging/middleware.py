"""Logging middleware that adds OpenTelemetry integration to django-structlog."""

import time
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

    Works correctly in both WSGI (sync) and ASGI (async) deployments.
    The parent class handles async dispatch; ``prepare`` and ``handle_response``
    are called via ``sync_to_async`` in ASGI mode by the parent's ``__acall__``,
    so neither method ever runs on the event loop directly.
    """

    def prepare(self, request: HttpRequest) -> None:
        request.META["_o11y_start"] = time.perf_counter()
        super().prepare(request)
        # Read back the request_id django-structlog just bound so the span and
        # structlog context always share the same value.
        ctx = structlog.contextvars.get_merged_contextvars(
            structlog.get_logger(__name__)
        )
        request_id = ctx.get("request_id")
        if request_id:
            span = trace.get_current_span()
            if span.is_recording():
                span.set_attribute("request.id", request_id)

    def handle_response(self, request: HttpRequest, response: Any) -> None:
        start = request.META.get("_o11y_start")
        if start is not None:
            structlog.contextvars.bind_contextvars(
                duration_ms=round((time.perf_counter() - start) * 1000, 2)
            )
        super().handle_response(request, response)
