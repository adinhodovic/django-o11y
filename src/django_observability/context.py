"""Context management for custom tags and attributes.

This module provides utilities for adding custom business tags to traces and logs
at runtime. Use these helpers in your views, middleware, or business logic to add
contextual information that's relevant to your application.

Example usage:

    from django_observability.context import set_custom_tags, add_span_attribute

    def my_view(request):
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

import structlog
from opentelemetry import trace
from typing import Any


def set_custom_tags(tags: dict[str, Any]) -> None:
    """Set custom tags on both the current span (prefixed "custom.") and structlog context."""
    span = trace.get_current_span()
    if span.is_recording():
        for key, value in tags.items():
            span.set_attribute(f"custom.{key}", str(value))

    structlog.contextvars.bind_contextvars(**tags)


def add_span_attribute(key: str, value: Any) -> None:
    """Add a single attribute to the current span (prefixed "custom."), without touching logs."""
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute(f"custom.{key}", str(value))


def add_log_context(**kwargs: Any) -> None:
    """Add key-value pairs to structlog context only (not traces)."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_custom_context() -> None:
    """Clear all structlog context variables. Middleware handles this automatically; call manually in long-running tasks."""
    structlog.contextvars.clear_contextvars()


def get_current_trace_id() -> str | None:
    """Return the current trace ID as a hex string, or None if there is no active span."""
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        if ctx.trace_id:
            return format(ctx.trace_id, "032x")
    return None


def get_current_span_id() -> str | None:
    """Return the current span ID as a hex string, or None if there is no active span."""
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        if ctx.span_id:
            return format(ctx.span_id, "016x")
    return None
