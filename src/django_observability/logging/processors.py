"""
Custom structlog processors for Django Observability.

Includes the add_open_telemetry_spans processor from the blog post:
https://hodovi.cc/blog/django-development-and-production-logging/
"""

from typing import Any

from opentelemetry import trace


def add_open_telemetry_spans(_: Any, __: Any, event_dict: dict) -> dict:
    """
    Add OpenTelemetry span context to log events.

    Adds span_id, trace_id, and parent_span_id to log entries for correlation
    between logs and traces.

    Args:
        event_dict: The log event dictionary

    Returns:
        Modified event dictionary with span context
    """
    span = trace.get_current_span()
    if not span.is_recording():
        return event_dict

    ctx = span.get_span_context()
    parent = getattr(span, "parent", None)

    event_dict["span_id"] = f"{ctx.span_id:x}"
    event_dict["trace_id"] = f"{ctx.trace_id:x}"
    if parent:
        event_dict["parent_span_id"] = f"{parent.span_id:x}"

    return event_dict
