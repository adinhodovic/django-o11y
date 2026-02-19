# Usage guide

## Prometheus

Add `django_prometheus` and wrap your middleware:

```python
# settings.py
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

Use django-prometheus database and cache backends to get query and cache metrics:

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

## Per-environment configuration

```python
# settings/local.py
from .base import *

DJANGO_O11Y["LOGGING"]["FORMAT"] = "console"
DJANGO_O11Y["TRACING"]["SAMPLE_RATE"] = 1.0

# settings/production.py
from .base import *

DJANGO_O11Y["LOGGING"]["FORMAT"] = "json"
DJANGO_O11Y["TRACING"]["SAMPLE_RATE"] = 0.01
```

## Celery

Install the Celery extra:

```bash
pip install django-o11y[celery]
```

Enable in settings:

```python
DJANGO_O11Y = {
    # ...
    "CELERY": {
        "ENABLED": True,
    },
}

CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
```

When your Celery worker starts, observability is automatically set up via signals. For advanced use cases, you can call it manually:

```python
# config/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("myproject")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

from django_o11y.celery import setup_celery_o11y
setup_celery_o11y(app)
```

Use structlog in tasks for proper trace correlation:

```python
import structlog
from celery import shared_task
from django_o11y.context import set_custom_tags

logger = structlog.get_logger(__name__)

@shared_task(bind=True)
def process_order(self, order_id: int):
    set_custom_tags({
        "order_id": order_id,
        "task_type": "order_processing",
    })

    logger.info("order_processing_started", order_id=order_id)
    result = do_processing(order_id)
    logger.info("order_processing_completed", order_id=order_id)

    return result
```

Logs automatically include trace context:

```json
{
  "event": "order_processing_started",
  "order_id": 12345,
  "task_id": "a1b2c3d4-...",
  "trace_id": "abc123...",
  "span_id": "def456..."
}
```

## Custom metrics

Track business metrics using counters and histograms. Label names must be declared upfront at metric creation time (Prometheus convention).

```python
from django_o11y.metrics import counter, histogram

# Counter — declare label dimensions with labelnames=
payment_counter = counter(
    "payments_processed_total",
    description="Total payments processed",
    labelnames=["status", "method"],
)
payment_counter.add(1, {"status": "success", "method": "card"})
payment_counter.add(1, {"status": "failed", "method": "paypal"})

# Histogram — measure durations or sizes
payment_latency = histogram(
    "payment_processing_seconds",
    description="Payment processing time",
    unit="s",
    labelnames=["method"],
)

# Manual observation
payment_latency.record(0.532, {"method": "card"})

# Automatic timing via context manager
with payment_latency.time({"method": "card"}):
    result = process_payment()
```

Metrics are exposed on the standard `/metrics` endpoint alongside django-prometheus infrastructure metrics.

## Custom tags and context

Add business context to traces and logs:

```python
from django_o11y.context import (
    set_custom_tags,
    add_span_attribute,
    add_log_context,
    set_user_context,
)

def my_view(request):
    set_custom_tags({"tenant_id": "acme", "feature": "checkout_v2"})

    # User context (automatic if using AuthenticationMiddleware)
    set_user_context(
        user_id=str(request.user.id),
        username=request.user.username,
    )

    add_span_attribute("cache_hit", True)  # Traces only
    add_log_context(items_in_cart=5)       # Logs only

    return HttpResponse("OK")
```

| Function | Traces | Logs | Use Case |
|----------|--------|------|----------|
| `set_custom_tags()` | Yes | Yes | Business context |
| `add_span_attribute()` | Yes | No | Technical metrics |
| `add_log_context()` | No | Yes | Debug info |
| `set_user_context()` | Yes | Yes | User identification |

## Common patterns

### Multi-tenant applications

```python
class TenantMiddleware:
    def __call__(self, request):
        tenant = get_tenant_from_request(request)
        set_custom_tags({
            "tenant_id": tenant.id,
            "tenant_tier": tenant.subscription_tier,
        })
        return self.get_response(request)
```

### Feature flags

```python
def checkout_view(request):
    variant = get_feature_flag("new_checkout", request.user)
    set_custom_tags({"experiment": "new_checkout", "variant": variant})

    if variant == "B":
        return new_checkout(request)
    return old_checkout(request)
```

### Error tracking

```python
import structlog

logger = structlog.get_logger(__name__)

try:
    process_payment(order)
except PaymentError as e:
    logger.error(
        "payment_failed",
        error_type=type(e).__name__,
        error_message=str(e),
        order_id=order.id,
    )
    raise
```

## Verification

Run the built-in health check:

```bash
python manage.py o11y check
```

This checks configuration, tests OTLP endpoint connectivity, verifies required packages, and sends a test trace.

Check the metrics endpoint:

```bash
curl http://localhost:8000/metrics
```

Check traces are being received:

```bash
curl http://localhost:8000/
curl 'http://localhost:3200/api/search?tags=service.name=my-app' | jq
```

## Troubleshooting

**No traces in Tempo**

Check OTLP endpoint is reachable:
```bash
curl -v http://localhost:4317
curl 'http://localhost:3200/api/search?tags=service.name=YOUR-APP-NAME'
```

**No metrics**

Check the endpoint and ensure `django_prometheus` is in `INSTALLED_APPS`:
```bash
curl http://localhost:8000/metrics
```

**Database errors**

Use django-prometheus backends:
```python
# Correct
"ENGINE": "django_prometheus.db.backends.postgresql"

# Wrong
"ENGINE": "django_o11y.db.backends.postgresql"
```

**Silent Celery instrumentation failure**

Install the required package:
```bash
pip install opentelemetry-instrumentation-celery
```

The system will warn you at startup if this package is missing.

**Configuration errors**

Configuration is validated at startup:
```
ImproperlyConfigured: django-o11y configuration errors:
  • TRACING.SAMPLE_RATE must be between 0.0 and 1.0, got 1.5
```

**Logs not structured**

Use `structlog.get_logger()` not `logging.getLogger()`, and use kwargs not f-strings:
```python
# Good
logger.info("user_logged_in", user_id=user_id)

# Bad
logger.info(f"User {user_id} logged in")
```

**Keep metric tag cardinality low** (under 100 unique values per tag).
