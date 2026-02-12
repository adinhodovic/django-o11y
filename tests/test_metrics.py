"""Tests for custom metrics helpers."""

import pytest
import time
from unittest.mock import Mock, patch
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader


@pytest.fixture
def metrics_setup():
    """Set up metrics with in-memory reader for testing."""
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])

    with patch("opentelemetry.metrics.get_meter_provider", return_value=provider):
        yield provider, reader


def test_metrics_module_exports():
    from django_observability.metrics import counter, histogram

    assert counter is not None
    assert histogram is not None
    assert callable(counter)
    assert callable(histogram)


def test_counter_creation(metrics_setup):
    from django_observability.metrics.custom import counter

    payment_counter = counter("payments.processed", "Total payments processed", "")

    assert payment_counter is not None
    assert payment_counter.name == "payments.processed"
    assert payment_counter.description == "Total payments processed"


def test_counter_add(metrics_setup):
    from django_observability.metrics.custom import counter
    from unittest.mock import Mock

    test_counter = counter("test.counter", "Test counter")

    with patch.object(test_counter.metric, "add") as mock_add:
        test_counter.add(1)
        test_counter.add(5)
        test_counter.add(10)

        assert mock_add.call_count == 3


def test_counter_add_with_attributes(metrics_setup):
    from django_observability.metrics.custom import counter

    payment_counter = counter("payments.count", "Payment count")

    with patch.object(payment_counter.metric, "add") as mock_add:
        payment_counter.add(1, {"status": "success", "method": "card"})
        payment_counter.add(1, {"status": "failed", "method": "paypal"})

        assert mock_add.call_count == 2
        mock_add.assert_called_with(
            1, attributes={"status": "failed", "method": "paypal"}
        )


def test_counter_add_with_none_attributes(metrics_setup):
    from django_observability.metrics.custom import counter

    test_counter = counter("test.counter", "Test")
    test_counter.add(1, None)


def test_histogram_creation(metrics_setup):
    from django_observability.metrics.custom import histogram

    latency_histogram = histogram("api.latency", "API request latency", "s")

    assert latency_histogram is not None
    assert latency_histogram.name == "api.latency"
    assert latency_histogram.description == "API request latency"


def test_histogram_record(metrics_setup):
    from django_observability.metrics.custom import histogram

    latency = histogram("request.latency", "Request duration", "s")

    with patch.object(latency.metric, "record") as mock_record:
        latency.record(0.123)
        latency.record(0.456)
        latency.record(0.789)

        assert mock_record.call_count == 3


def test_histogram_record_with_attributes(metrics_setup):
    from django_observability.metrics.custom import histogram

    latency = histogram("endpoint.latency", "Endpoint latency", "s")

    with patch.object(latency.metric, "record") as mock_record:
        latency.record(0.1, {"endpoint": "/api/users", "method": "GET"})
        latency.record(0.5, {"endpoint": "/api/orders", "method": "POST"})

        assert mock_record.call_count == 2
        mock_record.assert_called_with(
            0.5, attributes={"endpoint": "/api/orders", "method": "POST"}
        )


def test_histogram_record_with_none_attributes(metrics_setup):
    from django_observability.metrics.custom import histogram

    test_histogram = histogram("test.histogram", "Test")
    test_histogram.record(1.23, None)


def test_histogram_time_context_manager(metrics_setup):
    from django_observability.metrics.custom import histogram

    latency = histogram("operation.duration", "Operation duration", "s")

    with patch.object(latency.metric, "record") as mock_record:
        with latency.time({"operation": "test"}):
            time.sleep(0.01)

        assert mock_record.call_count == 1
        call_args = mock_record.call_args
        assert call_args[1]["attributes"] == {"operation": "test"}
        assert call_args[0][0] > 0


def test_histogram_time_without_attributes(metrics_setup):
    from django_observability.metrics.custom import histogram

    latency = histogram("simple.duration", "Duration")

    with patch.object(latency.metric, "record") as mock_record:
        with latency.time():
            time.sleep(0.01)

        assert mock_record.call_count == 1
        call_args = mock_record.call_args
        assert call_args[0][0] > 0


def test_histogram_time_with_exception(metrics_setup):
    from django_observability.metrics.custom import histogram

    latency = histogram("error.duration", "Duration with error")

    with patch.object(latency.metric, "record") as mock_record:
        try:
            with latency.time({"status": "error"}):
                raise ValueError("Test error")
        except ValueError:
            pass

        assert mock_record.call_count == 1
        call_args = mock_record.call_args
        assert call_args[1]["attributes"] == {"status": "error"}


def test_counter_wrapper_attributes():
    from django_observability.metrics.custom import CounterWrapper
    from unittest.mock import Mock

    mock_counter = Mock()
    wrapper = CounterWrapper(mock_counter, "test.counter", "Test counter")

    assert wrapper.metric == mock_counter
    assert wrapper.name == "test.counter"
    assert wrapper.description == "Test counter"


def test_histogram_wrapper_attributes():
    from django_observability.metrics.custom import HistogramWrapper
    from unittest.mock import Mock

    mock_histogram = Mock()
    wrapper = HistogramWrapper(mock_histogram, "test.histogram", "Test histogram")

    assert wrapper.metric == mock_histogram
    assert wrapper.name == "test.histogram"
    assert wrapper.description == "Test histogram"


def test_metric_wrapper_base_class():
    from django_observability.metrics.custom import MetricWrapper
    from unittest.mock import Mock

    mock_metric = Mock()
    wrapper = MetricWrapper(mock_metric, "test.metric", "Test metric")

    assert wrapper.metric == mock_metric
    assert wrapper.name == "test.metric"
    assert wrapper.description == "Test metric"


def test_multiple_counters(metrics_setup):
    from django_observability.metrics.custom import counter

    counter1 = counter("metric.one", "First metric")
    counter2 = counter("metric.two", "Second metric")

    counter1.add(1)
    counter2.add(2)

    assert counter1.name != counter2.name


def test_multiple_histograms(metrics_setup):
    from django_observability.metrics.custom import histogram

    hist1 = histogram("duration.one", "First duration", "s")
    hist2 = histogram("duration.two", "Second duration", "ms")

    hist1.record(1.0)
    hist2.record(100.0)

    assert hist1.name != hist2.name


def test_counter_and_histogram_together(metrics_setup):
    from django_observability.metrics.custom import counter, histogram

    request_counter = counter("requests.total", "Total requests")
    request_latency = histogram("requests.duration", "Request duration", "s")

    request_counter.add(1, {"endpoint": "/api/test"})

    with request_latency.time({"endpoint": "/api/test"}):
        time.sleep(0.01)

    assert request_counter.name == "requests.total"
    assert request_latency.name == "requests.duration"
