"""Custom OpenTelemetry metrics helpers with exemplar support."""

from contextlib import contextmanager
from time import time
from typing import Any

from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram


class MetricWrapper:
    """Base wrapper for OpenTelemetry metrics."""

    def __init__(self, metric: Any, name: str, description: str):
        self.metric = metric
        self.name = name
        self.description = description


class CounterWrapper(MetricWrapper):
    """Wrapper for Counter metrics with exemplar support."""

    def __init__(self, counter: Counter, name: str, description: str):
        super().__init__(counter, name, description)

    def add(
        self, amount: int | float, attributes: dict[str, Any] | None = None
    ) -> None:
        self.metric.add(amount, attributes=attributes or {})


class HistogramWrapper(MetricWrapper):
    """Wrapper for Histogram metrics with timing support."""

    def __init__(self, histogram: Histogram, name: str, description: str):
        super().__init__(histogram, name, description)

    def record(self, value: float, attributes: dict[str, Any] | None = None) -> None:
        self.metric.record(value, attributes=attributes or {})

    @contextmanager
    def time(self, attributes: dict[str, Any] | None = None):
        """Context manager that records elapsed seconds."""
        start = time()
        try:
            yield
        finally:
            duration = time() - start
            self.record(duration, attributes)


def counter(name: str, description: str = "", unit: str = "") -> CounterWrapper:
    """Create and return an OTel Counter wrapped in CounterWrapper."""
    meter = metrics.get_meter(__name__)
    otel_counter = meter.create_counter(name=name, description=description, unit=unit)
    return CounterWrapper(otel_counter, name, description)


def histogram(name: str, description: str = "", unit: str = "") -> HistogramWrapper:
    """Create and return an OTel Histogram wrapped in HistogramWrapper."""
    meter = metrics.get_meter(__name__)
    otel_histogram = meter.create_histogram(
        name=name, description=description, unit=unit
    )
    return HistogramWrapper(otel_histogram, name, description)
