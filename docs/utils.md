# Utility Functions

This page documents the helper utilities for logs, traces, and custom metrics.

## Logging (`django_o11y.logging.utils`)

### `get_logger()`

Returns a structlog logger bound to the caller module name.

```python
from django_o11y.logging.utils import get_logger

logger = get_logger()
logger.info("checkout_started", order_id=order_id)
```

### `add_log_context(**kwargs)`

Binds key-value pairs to structlog context for the current request/task context.

```python
from django_o11y.logging.utils import add_log_context

add_log_context(tenant_id="acme", request_source="web")
```

### `clear_custom_context()`

Clears all bound structlog contextvars.

```python
from django_o11y.logging.utils import clear_custom_context

clear_custom_context()
```

## Tracing (`django_o11y.tracing.utils`)

### `get_tracer(name=None)`

Returns an OpenTelemetry tracer. If `name` is omitted, it infers the caller module name (same convention as `get_logger()`).

```python
from django_o11y.tracing.utils import get_tracer

tracer = get_tracer()
with tracer.start_as_current_span("checkout"):
    ...
```

### `set_custom_tags(tags)`

Adds tags to the active span and binds the same values to structlog context.

```python
from django_o11y.tracing.utils import set_custom_tags

set_custom_tags({"tenant_id": "acme", "plan": "pro"})
```

Tags are written as `custom.<key>` on spans.

### `add_span_attribute(key, value)`

Adds one `custom.<key>` attribute to the active span only.

```python
from django_o11y.tracing.utils import add_span_attribute

add_span_attribute("cart_size", len(cart.items))
```

### `get_current_trace_id()`

Returns the current trace ID as a 32-char hex string, or `None` if no recording span is active.

### `get_current_span_id()`

Returns the current span ID as a 16-char hex string, or `None` if no recording span is active.

### Internal Celery helpers

`is_celery_prefork_pool()` and `is_celery_fork_pool_worker()` are internal runtime helpers used by django-o11y Celery setup.

## Metrics (`django_o11y.metrics`)

### `counter(name, description="", unit="", labelnames=())`

Creates a Prometheus counter wrapper.

```python
from django_o11y.metrics import counter

payments_total = counter(
    "payments_processed_total",
    description="Total number of processed payments",
    labelnames=["status", "provider"],
)

payments_total.add(1, {"status": "success", "provider": "stripe"})
```

Use `add(amount=1, attributes=None)` to increment the metric.

### `histogram(name, description="", unit="", labelnames=(), buckets=...)`

Creates a Prometheus histogram wrapper with direct observations and timing context support.

```python
from django_o11y.metrics import histogram

checkout_latency = histogram(
    "checkout_seconds",
    description="Checkout processing latency",
    labelnames=["payment_method"],
)

checkout_latency.record(0.84, {"payment_method": "card"})

with checkout_latency.time({"payment_method": "card"}):
    process_checkout()
```

`time()` measures elapsed seconds and records it automatically.

## Notes

- Declare label names up front when creating metrics.
- `unit` is accepted for API consistency and future compatibility.
- Custom metrics are registered in the default Prometheus registry and exposed on your configured `/metrics` endpoint.
