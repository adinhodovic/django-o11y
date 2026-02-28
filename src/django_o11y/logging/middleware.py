"""Logging middleware that extends django-structlog with OpenTelemetry integration."""

import uuid
from asyncio import iscoroutinefunction
from typing import Any

from asgiref.sync import markcoroutinefunction
from django.http import HttpRequest
from django_structlog.middlewares import (
    RequestMiddleware as DjangoStructlogRequestMiddleware,
)
from opentelemetry import trace


class LoggingMiddleware(DjangoStructlogRequestMiddleware):
    """
    Extends django-structlog's RequestMiddleware with OTel span integration.

    All django-structlog behaviour (request_id, correlation_id, user_id, etc.) is
    inherited unchanged.  The only addition is setting the ``request.id`` span
    attribute so traces and logs share the same identifier.

    Works for both WSGI and ASGI deployments: the parent class marks itself as a
    coroutine function when ``get_response`` is async, and this subclass preserves
    that detection so the async path is used correctly on Daphne / Uvicorn.
    """

    def __init__(self, get_response: Any) -> None:
        super().__init__(get_response)
        # Re-apply the async marker in case our class definition shadowed it.
        # The parent already does this, but subclassing with a sync __call__
        # would break the detection — we override __call__ so we must redo it.
        if iscoroutinefunction(self.get_response):
            markcoroutinefunction(self)

    def __call__(self, request: HttpRequest) -> Any:
        if iscoroutinefunction(self):
            return self.__acall__(request)  # type: ignore[return-value]

        request_id = _get_request_id(request)
        _stamp_span(request_id)
        return super().__call__(request)

    async def __acall__(self, request: HttpRequest) -> Any:  # type: ignore[override]
        request_id = _get_request_id(request)
        _stamp_span(request_id)
        return await super().__acall__(request)


def _get_request_id(request: HttpRequest) -> str:
    return (
        request.headers.get("X-Request-ID")
        or request.META.get("HTTP_X_REQUEST_ID")
        or str(uuid.uuid4())
    )


def _stamp_span(request_id: str) -> None:
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("request.id", request_id)
