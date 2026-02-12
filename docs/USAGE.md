# Usage guide

## Custom tags and context

Add business context to traces and logs:

```python
from django_observability.context import (
    set_custom_tags,
    add_span_attribute,
    add_log_context,
    set_user_context,
)

def my_view(request):
    # Appears in traces and logs
    set_custom_tags({
        "tenant_id": "acme",
        "feature": "checkout_v2",
    })
    
    # User context (automatic if using AuthenticationMiddleware)
    set_user_context(
        user_id=str(request.user.id),
        username=request.user.username,
    )
    
    # Traces only
    add_span_attribute("cache_hit", True)
    
    # Logs only
    add_log_context(items_in_cart=5)
    
    return HttpResponse("OK")
```

### Reference

| Function | Traces | Logs | Use Case |
|----------|--------|------|----------|
| `set_custom_tags()` | Yes | Yes | Business context |
| `add_span_attribute()` | Yes | No | Technical metrics |
| `add_log_context()` | No | Yes | Debug info |
| `set_user_context()` | Yes | Yes | User identification |

## Custom metrics

Track business metrics with automatic trace correlation:

```python
from django_observability.metrics import counter, histogram, gauge

# Counter
payment_counter = counter(
    "payments.processed",
    description="Total payments processed"
)
payment_counter.add(1, {"status": "success", "method": "card"})

# Histogram (links to traces via exemplars)
payment_latency = histogram(
    "payments.latency",
    description="Payment processing time",
    unit="s"
)

# Manual
payment_latency.record(0.532, {"method": "card"})

# Or automatic
with payment_latency.time({"method": "card"}):
    result = process_payment()

# Gauge
active_connections = gauge(
    "db.connections.active",
    description="Active database connections"
)
active_connections.set(42)
```

### Decorators

```python
from django_observability.metrics import track_counter, track_histogram

@track_counter("api.calls", {"endpoint": "checkout"})
def checkout_api(request):
    return process_checkout(request)

@track_histogram("task.duration", {"task": "email"})
def send_email_task():
    send_email()
```

## Middleware order

```python
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    
    # Django middleware
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    
    # Observability (after auth)
    "django_observability.middleware.TracingMiddleware",
    "django_observability.middleware.LoggingMiddleware",
    
    # More Django middleware
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]
```

Place observability middleware after `AuthenticationMiddleware` so `request.user` is available.

## Celery tasks

Use structlog for proper trace correlation:

```python
import structlog
from celery import shared_task
from django_observability.context import set_custom_tags

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

Logs include trace context:

```json
{
  "event": "order_processing_started",
  "order_id": 12345,
  "task_id": "a1b2c3d4-...",
  "trace_id": "abc123...",
  "span_id": "def456..."
}
```

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
    
    set_custom_tags({
        "experiment": "new_checkout",
        "variant": variant,
    })
    
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

## Notes

Use `structlog.get_logger()` not `logging.getLogger()`.

Use kwargs in log messages:
```python
# Good
logger.info("user_logged_in", user_id=user_id)

# Bad
logger.info(f"User {user_id} logged in")
```

Keep metric tag cardinality low (under 100 unique values per tag).
