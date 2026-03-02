"""Tracing context and runtime helpers."""

import multiprocessing
import os
import sys
from importlib import import_module
from typing import Any

import structlog
from opentelemetry import trace
from opentelemetry.trace import Tracer


def get_tracer(name: str | None = None) -> Tracer:
    """Return an OpenTelemetry tracer, defaulting to the caller module."""
    tracer_name = name
    if tracer_name is None:
        frame = sys._getframe(1)
        tracer_name = frame.f_globals.get("__name__", __name__)
    return trace.get_tracer(tracer_name)


def set_custom_tags(tags: dict[str, Any]) -> None:
    """Set custom tags on the current span and structlog context."""
    span = trace.get_current_span()
    if span.is_recording():
        for key, value in tags.items():
            span.set_attribute(f"custom.{key}", str(value))

    structlog.contextvars.bind_contextvars(**tags)


def add_span_attribute(key: str, value: Any) -> None:
    """Add one ``custom.*`` attribute to the current span."""
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute(f"custom.{key}", str(value))


def get_current_trace_id() -> str | None:
    """Return the current trace id as hex, or ``None`` if not available."""
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        if ctx.trace_id:
            return format(ctx.trace_id, "032x")
    return None


def get_current_span_id() -> str | None:
    """Return the current span id as hex, or ``None`` if not available."""
    span = trace.get_current_span()
    if span.is_recording():
        ctx = span.get_span_context()
        if ctx.span_id:
            return format(ctx.span_id, "016x")
    return None


def is_celery_prefork_pool(argv: list[str] | None = None) -> bool:
    """Return ``True`` when a Celery worker runs with the prefork pool."""
    args = argv if argv is not None else sys.argv

    if not args or "worker" not in args:
        return False

    cmd = os.path.basename(args[0])
    is_celery_cmd = cmd == "celery"
    is_python_module = any(
        arg == "-m" and idx + 1 < len(args) and args[idx + 1] == "celery"
        for idx, arg in enumerate(args)
    )
    if not (is_celery_cmd or is_python_module):
        return False

    for idx, arg in enumerate(args):
        if arg.startswith("--pool="):
            return arg.split("=", 1)[1] == "prefork"
        if arg in {"-P", "--pool"} and idx + 1 < len(args):
            return args[idx + 1] == "prefork"

    return True


def is_celery_fork_pool_worker() -> bool:
    """Return ``True`` inside a Celery prefork child process."""
    process_name = multiprocessing.current_process().name
    if process_name.startswith("ForkPoolWorker"):
        return True

    try:
        process = import_module("billiard.process")
        return process.current_process().name.startswith("ForkPoolWorker")
    except Exception:
        return False
