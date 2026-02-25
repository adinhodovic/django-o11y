"""Custom Prometheus metrics helpers."""

from contextlib import contextmanager
from time import perf_counter
from typing import Any

from prometheus_client import REGISTRY as DEFAULT_REGISTRY
from prometheus_client import Counter, Histogram


class MetricWrapper:
    """Base wrapper for Prometheus metrics."""

    def __init__(self, metric: Any, name: str, description: str):
        self.metric = metric
        self.name = name
        self.description = description


class CounterWrapper(MetricWrapper):
    """Wrapper for Counter metrics."""

    def __init__(
        self,
        counter: Counter,
        name: str,
        description: str,
        labelnames: tuple[str, ...] = (),
    ):
        super().__init__(counter, name, description)
        self.labelnames = labelnames

    def add(
        self, amount: int | float = 1, attributes: dict[str, Any] | None = None
    ) -> None:
        if self.labelnames:
            self.metric.labels(**(attributes or {})).inc(amount)
        else:
            self.metric.inc(amount)


class HistogramWrapper(MetricWrapper):
    """Wrapper for Histogram metrics with timing support."""

    def __init__(
        self,
        histogram: Histogram,
        name: str,
        description: str,
        labelnames: tuple[str, ...] = (),
    ):
        super().__init__(histogram, name, description)
        self.labelnames = labelnames

    def record(self, value: float, attributes: dict[str, Any] | None = None) -> None:
        if self.labelnames:
            self.metric.labels(**(attributes or {})).observe(value)
        else:
            self.metric.observe(value)

    @contextmanager
    def time(self, attributes: dict[str, Any] | None = None):
        """Context manager that records elapsed seconds."""
        start = perf_counter()
        try:
            yield
        finally:
            duration = perf_counter() - start
            self.record(duration, attributes)


def counter(
    name: str,
    description: str = "",
    unit: str = "",
    labelnames: tuple[str, ...] | list[str] = (),
) -> CounterWrapper:
    """Create and return a Prometheus Counter wrapped in CounterWrapper."""
    label_tuple = tuple(labelnames)
    prom_counter = Counter(
        name,
        description,
        labelnames=label_tuple,
        registry=DEFAULT_REGISTRY,
    )
    return CounterWrapper(prom_counter, name, description, label_tuple)


def histogram(
    name: str,
    description: str = "",
    unit: str = "",
    labelnames: tuple[str, ...] | list[str] = (),
    buckets: tuple[float, ...] = Histogram.DEFAULT_BUCKETS,
) -> HistogramWrapper:
    """Create and return a Prometheus Histogram wrapped in HistogramWrapper."""
    label_tuple = tuple(labelnames)
    prom_histogram = Histogram(
        name,
        description,
        labelnames=label_tuple,
        buckets=buckets,
        registry=DEFAULT_REGISTRY,
    )
    return HistogramWrapper(prom_histogram, name, description, label_tuple)
