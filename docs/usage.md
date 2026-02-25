# Usage guide

## Quick start

### Installation

```bash
pip install django-o11y
```

For everything:

```bash
pip install django-o11y[all]
```

Or pick what you need:

| Extra | Adds |
| ----- | ---- |
| `django-o11y[celery]` | Celery tracing and structured task logs |
| `django-o11y[profiling]` | Pyroscope continuous profiling |
| `django-o11y[postgres]` | OpenTelemetry traces for psycopg2 / psycopg (v3) queries |
| `django-o11y[redis]` | OpenTelemetry traces for Redis/cache operations |
| `django-o11y[http]` | OpenTelemetry traces for outbound `requests`, `urllib3`, `urllib`, and `httpx` calls |
| `django-o11y[aws]` | OpenTelemetry traces for AWS SDK calls via boto3/botocore (enable via `TRACING.AWS_ENABLED`) |
| `django-o11y[dev-logging]` | Rich exception formatting in dev logs |
| `django-o11y[all]` | Everything |

### Basic setup

Add to your Django settings:

```python
from django_o11y.logging.setup import build_logging_dict

LOGGING = build_logging_dict()

INSTALLED_APPS = [
    "django_prometheus",
    "django_o11y",
    # ...
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",

    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",

    # After auth so request.user is available
    "django_o11y.tracing.middleware.TracingMiddleware",
    "django_o11y.logging.middleware.LoggingMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    "django_prometheus.middleware.PrometheusAfterMiddleware",
]
```

---

## Management command

The `o11y` management command has two subcommand groups: `stack` for running the local observability stack, and `check` for verifying your setup.

### stack

Starts a Docker Compose stack and imports the Grafana dashboards. Stack configs are written to `~/.django-o11y/` on first run.

| Service | Image | Purpose |
| ------- | ----- | ------- |
| Grafana | `grafana/grafana` | Dashboards — auto-imported from Grafana.com on startup, no login required |
| Prometheus | `prom/prometheus` | Scrapes `/metrics` from your app; native histograms and exemplar storage enabled |
| Tempo | `grafana/tempo` | Receives OTLP traces from Alloy |
| Loki | `grafana/loki` | Receives logs from Alloy |
| Pyroscope | `grafana/pyroscope` | Receives continuous profiling data |
| Alloy | `grafana/alloy` | OTLP receiver (ports 4317/4318), forwards to Tempo/Loki/Pyroscope; also tails the dev log file and Docker container logs |
| celery-exporter | `danihodovic/celery-exporter` | Added automatically when `CELERY.ENABLED` is `True` and a broker URL is detected in Django or Celery settings |

```bash
# Start
python manage.py o11y stack start

# App running in Docker with a custom container name
python manage.py o11y stack start --app-url django-app:8000 --app-container myapp

# Stop
python manage.py o11y stack stop

# Restart without recreating containers
python manage.py o11y stack restart

# Show running services
python manage.py o11y stack status

# Tail logs (last 50 lines)
python manage.py o11y stack logs

# Follow log output
python manage.py o11y stack logs --follow
```

`--app-url` controls where Prometheus scrapes `/metrics` (default: `host.docker.internal:8000`). `--app-container` sets the Docker container name Alloy tails for logs (default: `django-app`).

### check

Checks your configuration, tests the OTLP endpoint, verifies installed packages, and sends a test trace.

```bash
python manage.py o11y check
```

---

## Metrics

### Django metrics

Django metrics are provided by [django-prometheus](https://github.com/korfuri/django-prometheus). It instruments request/response cycles, database queries, cache operations, and model saves. The Grafana dashboards and alerts are sourced from [django-mixin](https://github.com/adinhodovic/django-mixin).

Migration metrics (`django_migrations_applied_total`, `django_migrations_unapplied_total`) are enabled automatically. They power the migrations panel in the Django Overview dashboard and the `DjangoMigrationsUnapplied` alert. To disable them:

```python
DJANGO_O11Y = {
    "METRICS": {"EXPORT_MIGRATIONS": False},
}
```

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
from django_o11y import get_urls

urlpatterns = [
    # ...
] + get_urls()
```

`get_urls()` adds the Prometheus metrics endpoint at the path configured by `METRICS.PROMETHEUS_ENDPOINT` (default `/metrics`). Returns an empty list when `METRICS.PROMETHEUS_ENABLED` is `False`.

### Celery metrics

Celery metrics are exported by [celery-exporter](https://github.com/danihodovic/celery-exporter), a standalone Prometheus exporter that connects to your broker and exposes task state, queue length, and worker status. The Grafana dashboards and alerts are sourced from the [celery-mixin](https://github.com/danihodovic/celery-exporter/tree/master/celery-mixin) bundled within celery-exporter.

celery-exporter is added to the local dev stack automatically when `CELERY.ENABLED` is `True` and a broker URL is found in your Django or Celery settings (`CELERY_BROKER_URL` or `broker_url`). See the [celery-exporter docs](https://github.com/danihodovic/celery-exporter) for production deployment.

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

Structured logging via [Structlog](https://www.structlog.org/). Every log line includes `trace_id` and `span_id`, so you can jump from a log entry directly to the trace in Grafana.

### Setup

Call `build_logging_dict()` in each settings file. The defaults are keyed off `DEBUG`, so most of the difference between environments is handled automatically.

**`settings/local.py`**

```python
from django_o11y.logging.setup import build_logging_dict

LOGGING = build_logging_dict()
# DEBUG=True: console format, colorized, file output to /tmp/django-o11y/django.log
```

**`settings/production.py`**

```python
from django_o11y.logging.setup import build_logging_dict

LOGGING = build_logging_dict()
# DEBUG=False: JSON format, no file output
```

**`settings/test.py`**

```python
from django_o11y.logging.setup import build_logging_dict

LOGGING = build_logging_dict({"LEVEL": "WARNING", "FILE_ENABLED": False})
# Quiet in tests regardless of DEBUG
```

### Usage

```python
from django_o11y.logging.utils import get_logger

logger = get_logger()

logger.info("order_placed", order_id=order_id, amount=total)
logger.error("payment_failed", error=str(e), order_id=order_id)
```

`get_logger()` infers the module name automatically — no need to pass `__name__`. Use keyword arguments, not f-strings. This keeps logs machine-readable and queryable in Loki.

### Output formats

Development (`DEBUG=True`) — colorized console:

```text
2026-02-12T10:30:45 [info     ] order_placed    order_id=123 amount=49.99 [views.py:42]
```

Production (`DEBUG=False`) — JSON with trace correlation:

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

The format switches automatically based on `DEBUG`. Override it:

```python
LOGGING = build_logging_dict({"FORMAT": "json", "LEVEL": "INFO", ...})
```

Or via env var: `DJANGO_O11Y_LOGGING_FORMAT=json`.

### Log file (dev only)

When `DEBUG=True`, logs are also written as JSON to `/tmp/django-o11y/django.log`. The local dev stack (`o11y stack start`) tails this file with Alloy and ships it to Loki, so logs show up in Grafana without needing OTLP push enabled. Useful when running `runserver` or `runserver_plus` directly on the host.

Override the path:

```bash
DJANGO_O11Y_LOGGING_FILE_PATH=/var/log/myapp/django.log
```

Disable it:

```bash
DJANGO_O11Y_LOGGING_FILE_ENABLED=false
```

### Extending the config

Pass `extra` to deep-merge additional loggers or handlers into the base dict:

```python
from django_o11y.logging.setup import build_logging_dict

LOGGING = build_logging_dict(extra={
    "loggers": {
        "myapp": {"level": "DEBUG"},
        "myapp.payments": {"level": "WARNING"},
    },
})
```

Nested dicts are merged rather than replaced, so you only need to specify what you want to change.

### Adding context

Attach extra fields to all logs within the current request or task:

```python
from django_o11y.logging.utils import add_log_context
from django_o11y.tracing.utils import set_custom_tags

# Logs only
add_log_context(tenant_id="acme", checkout_variant="B")

# Logs + traces
set_custom_tags({"tenant_id": "acme", "feature": "checkout_v2"})
```

---

## Profiling

Continuous profiling via [Pyroscope](https://pyroscope.io/). Disabled by default. The Python SDK only supports push mode.

### Enable

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

Profiles are pushed to Pyroscope on startup. View them in Grafana under **Explore → Pyroscope**.

For Celery prefork workers, profiling is initialized in each worker child process (post-fork), not in the prefork parent process.


### Custom tags

Tag profiles with extra context for filtering:

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

Distributed tracing via [OpenTelemetry](https://opentelemetry.io/). Requests, database queries, cache operations, and outbound HTTP calls are all instrumented without any code changes.

### What gets instrumented

- Every HTTP request: span per view with status code, route, and user ID
- Database queries: span per query (requires django-prometheus DB backend)
- Outbound HTTP: spans for `requests`, `urllib3`, `urllib`, and `httpx` calls (requires `django-o11y[http]`)
- Redis: spans for cache operations (requires `django-o11y[redis]`)
- Celery tasks: span per task, linked to the request that triggered it (requires `django-o11y[celery]`)
- AWS SDK: spans for boto3/botocore calls — S3, SQS, SES, etc. (requires `django-o11y[aws]` and `TRACING.AWS_ENABLED: True`)

### Configuration

```python
DJANGO_O11Y = {
    "TRACING": {
        "ENABLED": True,          # default: False
        "OTLP_ENDPOINT": "http://localhost:4317",
        "SAMPLE_RATE": 1.0,       # 1.0 = 100%; default is 1.0 in DEBUG, 0.01 otherwise
    }
}
```

To disable tracing entirely, set `ENABLED: False` or `DJANGO_O11Y_TRACING_ENABLED=false`.

### Adding custom context

```python
from django_o11y.tracing.utils import set_custom_tags, add_span_attribute

def checkout_view(request):
    # Attached to both the trace span and all logs in this request
    set_custom_tags({"tenant_id": "acme", "experiment": "new_checkout"})

    # Span only
    add_span_attribute("cart_size", len(cart.items))


```

| Function | Trace span | Logs | Use case |
| -------- | ---------- | ---- | -------- |
| `set_custom_tags()` | Yes | Yes | Business context |
| `add_span_attribute()` | Yes | No | Technical span data |
| `add_log_context()` | No | Yes | Debug info |

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

Celery signals wire everything up when the worker starts. Each task gets a trace span linked to the originating request, and structured logs with `trace_id`/`span_id`.

To reduce span loss in prefork workers, django-o11y force-flushes tracing on `worker_process_shutdown`.

```python
import structlog
from celery import shared_task
from django_o11y.tracing.utils import set_custom_tags

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
