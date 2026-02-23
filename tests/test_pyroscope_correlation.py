"""Tests for pyroscope trace/profile correlation span processor."""

from types import SimpleNamespace
from unittest.mock import Mock

from django_o11y.tracing.pyroscope import PyroscopeCorrelationSpanProcessor


def _span(span_id: int, *, parent=None):
    return SimpleNamespace(
        context=SimpleNamespace(span_id=span_id),
        parent=parent,
        set_attribute=Mock(),
    )


def test_processor_supports_two_argument_pyroscope_api():
    module = SimpleNamespace(
        add_thread_tag=Mock(),
        remove_thread_tag=Mock(),
    )
    processor = PyroscopeCorrelationSpanProcessor(module)

    span = _span(1)
    processor.on_start(span)
    processor.on_end(span)

    module.add_thread_tag.assert_called_once_with("span_id", "0000000000000001")
    module.remove_thread_tag.assert_called_once_with("span_id", "0000000000000001")


def test_processor_supports_three_argument_pyroscope_api():
    class Module:
        def __init__(self):
            self.add_calls = []
            self.remove_calls = []

        def add_thread_tag(self, thread_id, key, value):
            self.add_calls.append((thread_id, key, value))

        def remove_thread_tag(self, thread_id, key, value):
            self.remove_calls.append((thread_id, key, value))

    module = Module()
    processor = PyroscopeCorrelationSpanProcessor(module)

    span = _span(2)
    processor.on_start(span)
    processor.on_end(span)

    assert len(module.add_calls) == 1
    assert len(module.remove_calls) == 1
    assert module.add_calls[0][1:] == ("span_id", "0000000000000002")
    assert module.remove_calls[0][1:] == ("span_id", "0000000000000002")
