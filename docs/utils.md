# Utility functions

Helper functions for logs, traces, and custom metrics provided by [django-o11y](https://github.com/adinhodovic/django-o11y).

Some of these are thin wrappers around [structlog](https://www.structlog.org/) or [OpenTelemetry](https://opentelemetry.io/) primitives. The point is to give your codebase a single import path for observability calls, so you're not scattering direct structlog or OTel imports across every module. If you ever need to swap an implementation detail, there's one place to change it.

## Logging (`django_o11y.logging.utils`)

### get_logger

Returns a structlog logger bound to the caller module.

```python
from django_o11y.logging.utils import get_logger

logger = get_logger()
logger.info("checkout_started", order_id=order_id)
```

### add_log_context

Adds key-value pairs to structlog context for the current request or task.

```python
from django_o11y.logging.utils import add_log_context

add_log_context(tenant_id="acme", request_source="web")
```

### clear_custom_context

Clears all bound structlog contextvars.

```python
from django_o11y.logging.utils import clear_custom_context

clear_custom_context()
```

### add_severity

Structlog processor that injects a GCP-compatible numeric `severity` field into log events. Only needed if you build a custom processor chain outside of `build_logging_dict()`, or if you ship logs to Google Cloud Logging.

```python
from django_o11y.logging.utils import add_severity
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        add_severity,
        # ...
    ]
)
```

Maps standard levels to [Cloud Logging severity values](https://cloud.google.com/logging/docs/reference/v2/rest/v2/LogEntry#logseverity): `debug` → 100, `info` → 200, `warning` → 400, `error` → 500, `critical` → 600. Unknown or missing levels fall back to `0` (`DEFAULT`).

### add_open_telemetry_spans

Structlog processor that injects `trace_id`, `span_id`, and `parent_span_id` from the active OpenTelemetry span. [django-o11y](https://github.com/adinhodovic/django-o11y) includes this automatically. Only needed if you build a custom processor chain outside of `build_logging_dict()`.

```python
from django_o11y.logging.utils import add_open_telemetry_spans
import structlog

structlog.configure(
    processors=[
        add_open_telemetry_spans,
        # ...
    ]
)
```

Fields are omitted when no recording span is active.


## Tracing (`django_o11y.tracing.utils`)

### get_tracer

Returns an OpenTelemetry tracer. If `name` is omitted, uses the caller module (same rule as `get_logger`).

```python
from django_o11y.tracing.utils import get_tracer

tracer = get_tracer()
with tracer.start_as_current_span("checkout"):
    ...
```

### set_custom_tags

Adds tags to the active span and binds the same values to structlog context.

```python
from django_o11y.tracing.utils import set_custom_tags

set_custom_tags({"tenant_id": "acme", "plan": "pro"})
```

Tags are written as `custom.<key>` on spans.

### add_span_attribute

Adds one `custom.<key>` attribute to the active span only.

```python
from django_o11y.tracing.utils import add_span_attribute

add_span_attribute("cart_size", len(cart.items))
```

### get_current_trace_id

Returns the current trace ID as a 32-char hex string, or `None` if no recording span is active.

```python
from django_o11y.tracing.utils import get_current_trace_id

trace_id = get_current_trace_id()
if trace_id:
    send_to_external_system(trace_id=trace_id)
```

### get_current_span_id

Returns the current span ID as a 16-char hex string, or `None` if no recording span is active.

```python
from django_o11y.tracing.utils import get_current_span_id

span_id = get_current_span_id()
```


## Metrics (`django_o11y.metrics`)

### counter

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

### histogram

Creates a Prometheus histogram wrapper with direct observations and timing support.

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
