"""Pyroscope profile-to-trace correlation span processor."""

import inspect
import logging
import threading
from typing import Any

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor

logger = logging.getLogger("django_o11y.tracing")

PROFILE_ID_SPAN_ATTRIBUTE_KEY = "pyroscope.profile.id"
PROFILE_ID_PYROSCOPE_TAG_KEY = "span_id"


def _is_root_span(span: Span | ReadableSpan) -> bool:
    parent = span.parent
    return parent is None or bool(parent.is_remote)


def _get_span_id(span: Span | ReadableSpan) -> str:
    context = span.context
    if context is None:
        return "0000000000000000"
    return format(context.span_id, "016x")


class PyroscopeCorrelationSpanProcessor(SpanProcessor):
    """Attach a Pyroscope tag on root span start/end for trace correlation."""

    def __init__(self, pyroscope_module: Any) -> None:
        self._pyroscope = pyroscope_module
        self._add_arg_count = len(
            inspect.signature(pyroscope_module.add_thread_tag).parameters
        )
        self._remove_arg_count = len(
            inspect.signature(pyroscope_module.remove_thread_tag).parameters
        )

    def _add_tag(self, key: str, value: str) -> None:
        if self._add_arg_count == 2:
            self._pyroscope.add_thread_tag(key, value)
            return
        if self._add_arg_count == 3:
            self._pyroscope.add_thread_tag(threading.get_ident(), key, value)
            return
        logger.warning(
            "Unsupported pyroscope.add_thread_tag signature (%s args)",
            self._add_arg_count,
        )

    def _remove_tag(self, key: str, value: str) -> None:
        if self._remove_arg_count == 2:
            self._pyroscope.remove_thread_tag(key, value)
            return
        if self._remove_arg_count == 3:
            self._pyroscope.remove_thread_tag(threading.get_ident(), key, value)
            return
        logger.warning(
            "Unsupported pyroscope.remove_thread_tag signature (%s args)",
            self._remove_arg_count,
        )

    def on_start(
        self,
        span: Span,
        parent_context: Context | None = None,
    ) -> None:
        del parent_context
        if _is_root_span(span):
            span_id = _get_span_id(span)
            span.set_attribute(PROFILE_ID_SPAN_ATTRIBUTE_KEY, span_id)
            self._add_tag(PROFILE_ID_PYROSCOPE_TAG_KEY, span_id)

    def on_end(self, span: ReadableSpan) -> None:
        if _is_root_span(span):
            self._remove_tag(PROFILE_ID_PYROSCOPE_TAG_KEY, _get_span_id(span))

    def shutdown(self) -> None:
        return

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        del timeout_millis
        return True


def build_pyroscope_span_processor() -> SpanProcessor | None:
    """Build a Pyroscope span processor if the dependency is installed."""
    try:
        import pyroscope
    except ImportError:
        return None
    return PyroscopeCorrelationSpanProcessor(pyroscope)
