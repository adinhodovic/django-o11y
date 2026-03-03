"""Logging middleware that adds OpenTelemetry integration to django-structlog."""

import time
import uuid
from typing import Any

import structlog
from django.http import HttpRequest
from django_structlog.middlewares import (
    RequestMiddleware as DjangoStructlogRequestMiddleware,
)
from opentelemetry import trace

from django_o11y.logging.utils import get_logger

logger = get_logger()

_REQUEST_ID_HEADER = b"x-request-id"


def _extract_request_id(headers: list[tuple[bytes, bytes]]) -> str:
    for name, value in headers:
        if name.lower() == _REQUEST_ID_HEADER:
            return value.decode("latin-1")
    return str(uuid.uuid4())


def _extract_user_id(scope: dict[str, Any]) -> str | None:
    from django.utils.functional import empty

    user = scope.get("user")
    if user is None:
        return None

    wrapped = getattr(user, "_wrapped", user)
    if wrapped is None or wrapped is empty:
        return None

    is_auth = getattr(wrapped, "is_authenticated", False)
    if callable(is_auth):
        try:
            is_auth = is_auth()
        except Exception:
            return None

    if not is_auth:
        return None

    uid = getattr(wrapped, "pk", None) or getattr(wrapped, "id", None)
    return str(uid) if uid is not None else None


class LoggingMiddleware(DjangoStructlogRequestMiddleware):
    """django-structlog request middleware with OTel span context.

    Sets ``request.id`` on the active span so traces and logs share the same
    identifier. Binds ``duration_ms`` to the structlog context so it appears
    on both ``request_finished`` and ``request_failed`` log lines.

    Works in WSGI and ASGI. The parent class handles async dispatch;
    ``prepare`` and ``handle_response`` run via ``sync_to_async`` in ASGI
    mode and never touch the event loop directly.
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


class ChannelsLoggingMiddleware:
    """ASGI middleware that adds structured logging to WebSocket connections."""

    def __init__(self, inner: Any) -> None:
        try:
            import channels  # noqa: F401  # pylint: disable=unused-import
        except ImportError as exc:
            raise ImportError(
                "ChannelsLoggingMiddleware requires 'channels'. "
                "Install it with: pip install django-o11y[channels]"
            ) from exc

        self.inner = inner

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Any,
        send: Any,
    ) -> None:
        if scope["type"] != "websocket":
            await self.inner(scope, receive, send)
            return

        headers = scope.get("headers", [])
        request_id = _extract_request_id(headers)
        path = scope.get("path", "")
        user_id = _extract_user_id(scope)

        structlog.contextvars.clear_contextvars()
        bind_kwargs: dict[str, Any] = {"request_id": request_id}
        if user_id is not None:
            bind_kwargs["user_id"] = user_id
        structlog.contextvars.bind_contextvars(**bind_kwargs)

        start = time.perf_counter()
        logger.info("websocket_connected", path=path)

        exc_info: BaseException | None = None
        try:
            await self.inner(scope, receive, send)
        except Exception as exc:
            exc_info = exc
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            if exc_info is not None:
                logger.error(
                    "websocket_error",
                    path=path,
                    duration_ms=duration_ms,
                    error=str(exc_info),
                    exc_info=exc_info,
                )
            else:
                logger.info(
                    "websocket_disconnected",
                    path=path,
                    duration_ms=duration_ms,
                )
            structlog.contextvars.clear_contextvars()
