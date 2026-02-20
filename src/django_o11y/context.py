"""Context management for custom tags and attributes.

This module provides utilities for adding custom business tags to traces and logs
at runtime. Use these helpers in your views, middleware, or business logic to add
contextual information that's relevant to your application.

Example usage:

    from django_o11y.context import get_logger, set_custom_tags, add_span_attribute

    logger = get_logger()

    def my_view(request):
        logger.info("order_placed", order_id=order_id, amount=total)

        # Add custom tags that appear in both traces and logs
        set_custom_tags({
            "tenant_id": request.tenant.id,
            "feature_flag": "checkout_v2",
            "user_tier": "premium",
        })

        # Add a single attribute just to the current span
        add_span_attribute("order_value", 99.99)

        # Your view logic here...
        return HttpResponse("OK")
"""

import sys
from typing import Any

import structlog
from opentelemetry import trace


def get_logger() -> structlog.BoundLoggerBase:
    """Return a structlog logger bound to the caller's module name.

    Equivalent to ``structlog.get_logger(__name__)`` but infers the name
    automatically, so callers don't need to pass ``__name__`` explicitly::

        from django_o11y.context import get_logger

        logger = get_logger()

        logger.info("order_placed", order_id=order_id, amount=total)
    """
    frame = sys._getframe(1)
    name: str = frame.f_globals.get("__name__", __name__)
    return structlog.get_logger(name)


def set_custom_tags(tags: dict[str, Any]) -> None:
    """Set custom tags on the current span (prefix "custom.") and structlog context."""
    span = trace.get_current_span()
    if span.is_recording():
        for key, value in tags.items():
            span.set_attribute(f"custom.{key}", str(value))

    structlog.contextvars.bind_contextvars(**tags)


def add_span_attribute(key: str, value: Any) -> None:
    """Add one attribute to the current span (prefix "custom."), logs unaffected."""
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute(f"custom.{key}", str(value))


def add_log_context(**kwargs: Any) -> None:
    """Add key-value pairs to structlog context only (not traces)."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_custom_context() -> None:
    """Clear all structlog context variables.

    Middleware handles this automatically; call manually in long-running tasks.
    """
    structlog.contextvars.clear_contextvars()


def get_current_trace_id() -> str | None:
    """Return the current trace ID as a hex string, or None if no active span."""
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        if ctx.trace_id:
            return format(ctx.trace_id, "032x")
    return None


def get_current_span_id() -> str | None:
    """Return the current span ID as a hex string, or None if no active span."""
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        if ctx.span_id:
            return format(ctx.span_id, "016x")
    return None
