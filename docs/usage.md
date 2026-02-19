# Usage guide

## Quick start

### Installation

```bash
pip install django-o11y
```

For all features:

```bash
pip install django-o11y[all]
```

Or pick what you need:

| Extra | Adds |
|-------|------|
| `django-o11y[celery]` | Celery tracing and structured task logs |
| `django-o11y[profiling]` | Pyroscope continuous profiling |
| `django-o11y[all]` | Everything |

### Basic setup

Add to your Django settings:

```python
INSTALLED_APPS = [
    "django_prometheus",
    "django_o11y",
    # ...
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",

    # Django middleware
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",

    # Observability (after auth so request.user is available)
    "django_o11y.middleware.TracingMiddleware",
    "django_o11y.middleware.LoggingMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    "django_prometheus.middleware.PrometheusAfterMiddleware",
]
```

That's it. django-o11y auto-configures tracing, logging, and metrics with sensible defaults on startup.

---

## Metrics

Metrics use [django-prometheus](https://github.com/korfuri/django-prometheus) for infrastructure metrics and a thin wrapper around `prometheus_client` for custom business metrics.

### Infrastructure metrics

Wrap your database and cache backends to get query counts, latency, and cache hit rates:

```python
DATABASES = {
    "default": {
        "ENGINE": "django_prometheus.db.backends.postgresql",
        # ...
    }
}

CACHES = {
    "default": {
        "BACKEND": "django_prometheus.cache.backends.redis.RedisCache",
        # ...
    }
}
```

Expose the metrics endpoint in your URL config:

```python
# urls.py
from django.urls import include, path

urlpatterns = [
    # ...
    path("", include("django_prometheus.urls")),
]
```

This exposes `/metrics` for Prometheus to scrape.

### Custom metrics

Track business events with counters and histograms. Label names must be declared upfront (Prometheus convention):

```python
from django_o11y.metrics import counter, histogram

# Counter
payment_counter = counter(
    "payments_processed_total",
    description="Total payments processed",
    labelnames=["status", "method"],
)
payment_counter.add(1, {"status": "success", "method": "card"})

# Histogram — manual observation
payment_latency = histogram(
    "payment_processing_seconds",
    description="Payment processing time",
    labelnames=["method"],
)
payment_latency.record(0.532, {"method": "card"})

# Histogram — automatic timing via context manager
with payment_latency.time({"method": "card"}):
    result = process_payment()
```

Custom metrics appear on the same `/metrics` endpoint alongside infrastructure metrics.

---

## Logs

Structured logging via [Structlog](https://www.structlog.org/) with automatic trace correlation. Every log line includes the active `trace_id` and `span_id`, so you can jump from a log entry directly to its trace in Grafana.

### Usage

Use `structlog.get_logger()` everywhere — not `logging.getLogger()`:

```python
import structlog

logger = structlog.get_logger(__name__)

logger.info("order_placed", order_id=order_id, amount=total)
logger.error("payment_failed", error=str(e), order_id=order_id)
```

Use keyword arguments, not f-strings. This keeps logs machine-readable and queryable in Loki.

### Development output (console)

```
2026-02-12T10:30:45 [info     ] order_placed    order_id=123 amount=49.99 [views.py:42]
```

### Production output (JSON)

```json
{
  "event": "order_placed",
  "order_id": 123,
  "amount": 49.99,
  "trace_id": "a1b2c3d4e5f6g7h8",
  "span_id": "i9j0k1l2",
  "timestamp": "2026-02-12T10:30:45.123Z",
  "level": "info",
  "logger": "myapp.views",
  "filename": "views.py",
  "lineno": 42
}
```

The format switches automatically: `console` when `DEBUG=True`, `json` when `DEBUG=False`.

### Configuration

```python
DJANGO_O11Y = {
    "LOGGING": {
        "FORMAT": "json",           # "console" or "json"
        "LEVEL": "INFO",
        "REQUEST_LEVEL": "INFO",    # django_structlog request logs
        "DATABASE_LEVEL": "WARNING" # set to "DEBUG" to log all SQL
    }
}
```

### Adding context

Attach extra fields to all logs within the current request or task:

```python
from django_o11y.context import add_log_context, set_custom_tags

# Logs only
add_log_context(tenant_id="acme", checkout_variant="B")

# Logs + traces
set_custom_tags({"tenant_id": "acme", "feature": "checkout_v2"})
```

---

## Profiling

Continuous profiling via [Pyroscope](https://pyroscope.io/). Disabled by default.

### Setup

Install the extra:

```bash
pip install django-o11y[profiling]
```

Enable in settings:

```python
DJANGO_O11Y = {
    "PROFILING": {
        "ENABLED": True,
        "PYROSCOPE_URL": "http://localhost:4040",
    }
}
```

Profiles are pushed to Pyroscope automatically on startup. View them in Grafana under **Explore → Pyroscope**.

### Custom tags

Tag profiles with business context for filtering:

```python
DJANGO_O11Y = {
    "PROFILING": {
        "ENABLED": True,
        "TAGS": {
            "region": "us-east-1",
            "tier": "premium",
        },
    }
}
```

---

## Traces

Distributed tracing via [OpenTelemetry](https://opentelemetry.io/). Django requests, database queries, cache operations, and outbound HTTP calls are all instrumented automatically.

### What is instrumented automatically

- Every HTTP request — span per view with status code, route, and user ID
- Database queries — span per query (requires django-prometheus DB backend)
- Outbound HTTP — spans for `requests` and `urllib3` calls (requires `django-o11y[http]`)
- Redis — spans for cache operations (requires `django-o11y[redis]`)
- Celery tasks — span per task, linked to the triggering request (requires `django-o11y[celery]`)

### Configuration

```python
DJANGO_O11Y = {
    "TRACING": {
        "OTLP_ENDPOINT": "http://localhost:4317",
        "SAMPLE_RATE": 1.0,   # 1.0 = 100%, use 0.01 in high-traffic prod
    }
}
```

### Adding custom context

```python
from django_o11y.context import set_custom_tags, add_span_attribute, set_user_context

def checkout_view(request):
    # Attached to both the trace span and all logs in this request
    set_custom_tags({"tenant_id": "acme", "experiment": "new_checkout"})

    # Span only
    add_span_attribute("cart_size", len(cart.items))

    # User identity on the span (called automatically if using AuthenticationMiddleware)
    set_user_context(user_id=str(request.user.id), username=request.user.username)
```

| Function | Trace span | Logs | Use case |
|----------|-----------|------|----------|
| `set_custom_tags()` | Yes | Yes | Business context |
| `add_span_attribute()` | Yes | No | Technical span data |
| `add_log_context()` | No | Yes | Debug info |
| `set_user_context()` | Yes | Yes | User identity |

### Celery

Install the extra:

```bash
pip install django-o11y[celery]
```

Enable in settings:

```python
DJANGO_O11Y = {
    "CELERY": {
        "ENABLED": True,
    }
}
```

Observability is set up automatically via Celery signals when the worker starts. Tasks get a trace span linked to the request that triggered them, structured logs with `trace_id`/`span_id`, and task lifecycle metrics.

```python
import structlog
from celery import shared_task
from django_o11y.context import set_custom_tags

logger = structlog.get_logger(__name__)

@shared_task
def process_order(order_id: int):
    set_custom_tags({"order_id": order_id})
    logger.info("order_processing_started", order_id=order_id)
    result = do_processing(order_id)
    logger.info("order_processing_completed", order_id=order_id)
    return result
```

### Verification

Run the built-in health check:

```bash
python manage.py o11y check
```

This checks the OTLP endpoint, installed packages, and sends a test trace you can find in Tempo.
