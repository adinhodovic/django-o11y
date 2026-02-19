"""Tests for custom metrics helpers."""

import time

import pytest
from prometheus_client import CollectorRegistry


@pytest.fixture
def registry():
    """Provide a fresh isolated Prometheus registry for each test."""
    return CollectorRegistry()


@pytest.fixture(autouse=True)
def patch_registry(registry, monkeypatch):
    """Patch the DEFAULT_REGISTRY used by counter() and histogram() factories."""
    import django_observability.metrics.custom as custom_mod

    monkeypatch.setattr(custom_mod, "DEFAULT_REGISTRY", registry)
    return registry


def test_counter_creation(registry):
    from django_observability.metrics.custom import counter

    payment_counter = counter("payments_processed_total", "Total payments processed")

    assert payment_counter is not None
    assert payment_counter.name == "payments_processed_total"
    assert payment_counter.description == "Total payments processed"


def test_counter_add(registry):
    from django_observability.metrics.custom import counter

    test_counter = counter("test_counter_total", "Test counter")

    test_counter.add(1)
    test_counter.add(5)
    test_counter.add(10)

    assert registry.get_sample_value("test_counter_total") == 16.0


def test_counter_add_with_attributes(registry):
    from django_observability.metrics.custom import counter

    payment_counter = counter(
        "payments_count_total", "Payment count", labelnames=["status", "method"]
    )

    payment_counter.add(1, {"status": "success", "method": "card"})
    payment_counter.add(3, {"status": "failed", "method": "paypal"})

    assert (
        registry.get_sample_value(
            "payments_count_total", {"status": "success", "method": "card"}
        )
        == 1.0
    )
    assert (
        registry.get_sample_value(
            "payments_count_total", {"status": "failed", "method": "paypal"}
        )
        == 3.0
    )


def test_counter_add_with_none_attributes(registry):
    from django_observability.metrics.custom import counter

    test_counter = counter("test_none_attrs_total", "Test")
    test_counter.add(1, None)

    assert registry.get_sample_value("test_none_attrs_total") == 1.0


def test_histogram_creation(registry):
    from django_observability.metrics.custom import histogram

    latency_histogram = histogram("api_latency_seconds", "API request latency", "s")

    assert latency_histogram is not None
    assert latency_histogram.name == "api_latency_seconds"
    assert latency_histogram.description == "API request latency"


def test_histogram_record(registry):
    from django_observability.metrics.custom import histogram

    latency = histogram("request_latency_seconds", "Request duration", "s")

    latency.record(0.123)
    latency.record(0.456)
    latency.record(0.789)

    assert registry.get_sample_value("request_latency_seconds_count") == 3.0


def test_histogram_record_with_attributes(registry):
    from django_observability.metrics.custom import histogram

    latency = histogram(
        "endpoint_latency_seconds",
        "Endpoint latency",
        "s",
        labelnames=["endpoint", "method"],
    )

    latency.record(0.1, {"endpoint": "/api/users", "method": "GET"})
    latency.record(0.5, {"endpoint": "/api/orders", "method": "POST"})

    assert (
        registry.get_sample_value(
            "endpoint_latency_seconds_count",
            {"endpoint": "/api/users", "method": "GET"},
        )
        == 1.0
    )
    assert (
        registry.get_sample_value(
            "endpoint_latency_seconds_count",
            {"endpoint": "/api/orders", "method": "POST"},
        )
        == 1.0
    )


def test_histogram_record_with_none_attributes(registry):
    from django_observability.metrics.custom import histogram

    test_histogram = histogram("test_histogram_seconds", "Test")
    test_histogram.record(1.23, None)

    assert registry.get_sample_value("test_histogram_seconds_count") == 1.0


def test_histogram_time_context_manager(registry):
    from django_observability.metrics.custom import histogram

    latency = histogram(
        "operation_duration_seconds",
        "Operation duration",
        "s",
        labelnames=["operation"],
    )

    with latency.time({"operation": "test"}):
        time.sleep(0.01)

    count = registry.get_sample_value(
        "operation_duration_seconds_count", {"operation": "test"}
    )
    total = registry.get_sample_value(
        "operation_duration_seconds_sum", {"operation": "test"}
    )
    assert count == 1.0
    assert total > 0


def test_histogram_time_without_attributes(registry):
    from django_observability.metrics.custom import histogram

    latency = histogram("simple_duration_seconds", "Duration")

    with latency.time():
        time.sleep(0.01)

    assert registry.get_sample_value("simple_duration_seconds_count") == 1.0
    assert registry.get_sample_value("simple_duration_seconds_sum") > 0


def test_histogram_time_with_exception(registry):
    from django_observability.metrics.custom import histogram

    latency = histogram(
        "error_duration_seconds", "Duration with error", labelnames=["status"]
    )

    try:
        with latency.time({"status": "error"}):
            raise ValueError("Test error")
    except ValueError:
        pass

    # Duration is still recorded even when the body raises
    assert (
        registry.get_sample_value("error_duration_seconds_count", {"status": "error"})
        == 1.0
    )


def test_multiple_counters(registry):
    from django_observability.metrics.custom import counter

    counter1 = counter("metric_one_total", "First metric")
    counter2 = counter("metric_two_total", "Second metric")

    counter1.add(1)
    counter2.add(2)

    assert counter1.name != counter2.name
    assert registry.get_sample_value("metric_one_total") == 1.0
    assert registry.get_sample_value("metric_two_total") == 2.0


def test_multiple_histograms(registry):
    from django_observability.metrics.custom import histogram

    hist1 = histogram("duration_one_seconds", "First duration", "s")
    hist2 = histogram("duration_two_seconds", "Second duration", "s")

    hist1.record(1.0)
    hist2.record(100.0)

    assert hist1.name != hist2.name
    assert registry.get_sample_value("duration_one_seconds_count") == 1.0
    assert registry.get_sample_value("duration_two_seconds_count") == 1.0


def test_counter_and_histogram_together(registry):
    from django_observability.metrics.custom import counter, histogram

    request_counter = counter(
        "requests_total", "Total requests", labelnames=["endpoint"]
    )
    request_latency = histogram(
        "requests_duration_seconds",
        "Request duration",
        "s",
        labelnames=["endpoint"],
    )

    request_counter.add(1, {"endpoint": "/api/test"})

    with request_latency.time({"endpoint": "/api/test"}):
        time.sleep(0.01)

    assert request_counter.name == "requests_total"
    assert request_latency.name == "requests_duration_seconds"
    assert registry.get_sample_value("requests_total", {"endpoint": "/api/test"}) == 1.0
    assert (
        registry.get_sample_value(
            "requests_duration_seconds_count", {"endpoint": "/api/test"}
        )
        == 1.0
    )


def test_counter_labelnames_stored(registry):
    from django_observability.metrics.custom import counter

    c = counter("labeled_counter_total", "Labeled", labelnames=["env", "region"])
    assert c.labelnames == ("env", "region")


def test_histogram_labelnames_stored(registry):
    from django_observability.metrics.custom import histogram

    h = histogram("labeled_histogram_seconds", "Labeled", labelnames=["env"])
    assert h.labelnames == ("env",)


def test_counter_no_labels_simple_inc(registry):
    """Counter with no labelnames uses plain .inc() without label lookup."""
    from django_observability.metrics.custom import counter

    c = counter("simple_counter_total", "No labels")
    c.add(7)
    assert registry.get_sample_value("simple_counter_total") == 7.0


def test_histogram_custom_buckets(registry):
    from django_observability.metrics.custom import histogram

    h = histogram(
        "custom_buckets_seconds",
        "Custom buckets",
        buckets=(0.01, 0.1, 1.0, 10.0),
    )
    h.record(0.05)

    assert registry.get_sample_value("custom_buckets_seconds_count") == 1.0
