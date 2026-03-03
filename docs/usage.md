# Usage guide

## Quick start

### Installation

```bash
pip install django-o11y
```

Install everything:

```bash
pip install django-o11y[all]
```

Or install only what you need:

| Extra | Adds |
| ----- | ---- |
| `django-o11y[celery]` | Celery tracing and structured task logs |
| `django-o11y[profiling]` | Pyroscope continuous profiling |
| `django-o11y[postgres]` | OpenTelemetry traces for psycopg2 / psycopg (v3) queries |
| `django-o11y[redis]` | OpenTelemetry traces for Redis/cache operations |
| `django-o11y[http]` | OpenTelemetry traces for outbound `requests`, `urllib3`, `urllib`, and `httpx` calls |
| `django-o11y[aws]` | OpenTelemetry traces for AWS SDK calls via boto3/botocore (enable via `TRACING.AWS_ENABLED`) |
| `django-o11y[channels]` | `ChannelsLoggingMiddleware` for Django Channels WebSocket observability |
| `django-o11y[dev-logging]` | Rich exception formatting in dev logs |
| `django-o11y[all]` | Everything |

### Basic setup

Add to your Django settings:

```python
from django_o11y.logging.setup import build_logging_dict

LOGGING = build_logging_dict()

INSTALLED_APPS = [
    "django_o11y",
    "django_prometheus",
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

### Utility function reference

Docs for log, trace, and metric helpers are in one page:

- [Utility functions](utils.md)

---

## Management command

The `o11y` management command has two groups: `stack` to run the local observability stack, and `check` to verify your setup.

### stack

> This stack is for local development only. It has no authentication and no persistent storage. For production, deploy your own stack or point `TRACING.OTLP_ENDPOINT` and `LOGGING.OTLP_ENDPOINT` at a managed service (Grafana Cloud, Honeycomb, Datadog, etc.). Locally, one command starts Grafana, Prometheus, Tempo, Loki, Pyroscope, and Alloy with the dashboards already imported.

Starts a Docker Compose stack and imports the Grafana dashboards. Stack configs are written to `${XDG_STATE_HOME:-~/.local/state}/django-o11y/` on first run. Override with `DJANGO_O11Y_STACK_DIR` when you want a project-local path.

| Service | Image | Purpose |
| ------- | ----- | ------- |
| Grafana | `grafana/grafana` | Dashboards — auto-imported from Grafana.com on startup, no login required |
| Prometheus | `prom/prometheus` | Scrapes `/metrics` from your app; native histograms and exemplar storage enabled |
| Tempo | `grafana/tempo` | Receives OTLP traces from Alloy |
| Loki | `grafana/loki` | Receives logs from Alloy |
| Pyroscope | `grafana/pyroscope` | Receives continuous profiling data |
| Alloy | `grafana/alloy` | OTLP receiver (ports 4317/4318), forwards to Tempo/Loki/Pyroscope; also tails the dev log file and Docker container logs |
| [celery-exporter](https://github.com/danihodovic/celery-exporter) | `danihodovic/celery-exporter` | Added automatically when `CELERY.ENABLED` is `True` and a broker URL is detected in Django or Celery settings |

```bash
# Start
python manage.py o11y stack start

# App running in Docker
python manage.py o11y stack start --app-url django-app:8000

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

`--app-url` controls where Prometheus scrapes `/metrics` (default: `host.docker.internal:8000`).

### check

Checks your config, tests the OTLP endpoint, verifies installed packages, and sends a test trace.

```bash
python manage.py o11y check
```

---

## Metrics

### Setup

Django metrics come from [django-prometheus](https://github.com/korfuri/django-prometheus), which instruments request/response cycles, database queries, cache operations, and model saves. Grafana dashboards and alerts are from [django-mixin](https://github.com/adinhodovic/django-mixin).

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

### Celery

Celery metrics come from [celery-exporter](https://github.com/danihodovic/celery-exporter), a standalone Prometheus exporter that connects to your broker and exposes task state, queue length, and worker status. Grafana dashboards and alerts are from the [celery-mixin](https://github.com/danihodovic/celery-exporter/tree/master/celery-mixin) bundled within celery-exporter.

[celery-exporter](https://github.com/danihodovic/celery-exporter) is added to the local dev stack automatically when `CELERY.ENABLED` is `True` and a broker URL is found in your Django or Celery settings (`CELERY_BROKER_URL` or `broker_url`). See the [celery-exporter docs](https://github.com/danihodovic/celery-exporter) for production deployment.

[django-prometheus](https://github.com/korfuri/django-prometheus) also runs inside Celery workers and exposes model metrics (insert, update, delete counts per model) via the worker metrics endpoint. Request and database query metrics are not available there — those only exist in the Django web process. If your tasks do a lot of database writes, model metrics are worth monitoring: they show which models are being mutated by background work and at what rate.

### Custom metrics

Track business events with counters and histograms. Label names must be declared up front (Prometheus convention):

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

For full metric helper signatures and examples, see [Utility functions](utils.md#metrics-django_o11ymetrics).

---

## Logs

Structured logging via [structlog](https://www.structlog.org/) and [django-structlog](https://github.com/jrobichaud/django-structlog). Every log line includes `trace_id` and `span_id` so logs and traces are correlated in Grafana.

### Logging Setup

Call `build_logging_dict()` in each environment settings module. A common split is `base.py`, `local.py`, `production.py` (or `prod.py`), and `test.py`.

`settings/base.py`

```python
DJANGO_O11Y = {
    "SERVICE_NAME": "my-django-app",
    "RESOURCE_ATTRIBUTES": {
        "deployment.environment": "local",
        "service.namespace": "web",
    },
    "TRACING": {"ENABLED": True},
    "METRICS": {"PROMETHEUS_ENABLED": True},
}

# Optional project-specific logger overrides reused by env-specific modules.
EXTRA_LOGGING: dict[str, object] = {}
```

`settings/local.py`

```python
from django_o11y.logging.setup import build_logging_dict

from .base import *  # noqa

DEBUG = True
LOGGING = build_logging_dict(extra=EXTRA_LOGGING)  # console logs + dev file sink
```

`settings/production.py`

```python
from django_o11y.logging.setup import build_logging_dict

from .base import *  # noqa

DEBUG = False
DJANGO_O11Y = {
    **DJANGO_O11Y,  # noqa: F405
    "RESOURCE_ATTRIBUTES": {
        **DJANGO_O11Y.get("RESOURCE_ATTRIBUTES", {}),  # noqa: F405
        "deployment.environment": "production",
    },
}
LOGGING = build_logging_dict(extra=EXTRA_LOGGING)  # JSON logs
```

`settings/test.py`

```python
from django_o11y.logging.setup import build_logging_dict

from .base import *  # noqa

DJANGO_O11Y = {
    **DJANGO_O11Y,  # noqa: F405
    "TRACING": {"ENABLED": False},
    "METRICS": {"PROMETHEUS_ENABLED": False},
    "CELERY": {"ENABLED": False},
    "PROFILING": {"ENABLED": False},
    "LOGGING": {"LEVEL": "WARNING", "FILE_ENABLED": False},
}
LOGGING = build_logging_dict(extra=EXTRA_LOGGING)
```

#### Usage

```python
from django_o11y.logging.utils import get_logger

logger = get_logger()

logger.info("order_placed", order_id=order_id, amount=total)
logger.error("payment_failed", error=str(e), order_id=order_id)
```

`get_logger()` infers the module name automatically — no need to pass `__name__`. Use keyword arguments, not f-strings. This keeps logs machine-readable and queryable in Loki.

For all logging helper APIs (`get_logger`, `add_log_context`, `clear_custom_context`), see [Utility functions](utils.md#logging-django_o11yloggingutils).

##### Output formats

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

##### Extending the config

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

#### File sink

When `DEBUG=True`, logs are also written as JSON to `${XDG_STATE_HOME:-~/.local/state}/django-o11y/<project>/django.log`. The local dev stack (`o11y stack start`) tails this file with Alloy and ships it to Loki, so logs show up in Grafana without needing OTLP push enabled. Useful when running `runserver` or `runserver_plus` directly on the host.

Override the path:

```bash
DJANGO_O11Y_LOGGING_FILE_PATH=/var/log/myapp/django.log
```

Disable it:

```bash
DJANGO_O11Y_LOGGING_FILE_ENABLED=false
```

### Celery Log Forwarding

When `CELERY.ENABLED` is `True`, [django-o11y](https://github.com/adinhodovic/django-o11y) hooks Celery's `setup_logging` signal to apply `settings.LOGGING` via `dictConfig` in each worker process. Worker logs use the same JSON format (or console format in dev) as the Django web process — no separate logging configuration needed.

This requires `LOGGING = build_logging_dict()` in your settings. Without it, `settings.LOGGING` is empty and worker processes fall back to plain-text Celery logs.

[django-structlog](https://github.com/jrobichaud/django-structlog) emits structured `task_started`, `task_succeeded`, and `task_failed` events automatically, each carrying `task_id`, `task_name`, `duration_ms`, and `trace_id`/`span_id`.

### WebSockets (Django Channels)

Add `ChannelsLoggingMiddleware` to your ASGI application. Place it inside `AuthMiddlewareStack` so `scope["user"]` is already resolved when the connection is logged:

```python
# asgi.py
from django_o11y.logging.middleware import ChannelsLoggingMiddleware

application = ProtocolTypeRouter({
    "http": django_http_handler,
    "websocket": AuthMiddlewareStack(
        ChannelsLoggingMiddleware(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
```

For every WebSocket connection this produces:

| Event | Fields |
| ----- | ------ |
| `websocket_connected` | `path`, `request_id`, `user_id` (if authenticated) |
| `websocket_disconnected` | same plus `duration_ms` |
| `websocket_error` | same plus `error` and `exc_info`; replaces `websocket_disconnected` when the consumer raises |

`http` and `lifespan` scopes pass through untouched.

---

## Profiling

Continuous profiling via [Pyroscope](https://pyroscope.io/) and [pyroscope-otel](https://github.com/grafana/otel-profiling-go). Disabled by default. The Python SDK only supports push mode.

### Profiling Setup

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

Profiles are pushed to Pyroscope on startup. View them in Grafana under Explore → Pyroscope.

### Celery Worker Profiling

For Celery prefork workers, profiling initialises in each worker child process after fork, not in the parent. [django-o11y](https://github.com/adinhodovic/django-o11y) handles the `worker_process_init` signal automatically.

---

## Traces

Distributed tracing via [OpenTelemetry](https://opentelemetry.io/) ([opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python)). Requests, database queries, cache operations, and outbound HTTP calls are instrumented automatically.

### Traces Setup

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

#### Automatic instrumentation

Instrumentation activates automatically when the relevant package is installed. Nothing extra to configure unless noted.

| What | Spans | Dependency |
| ---- | ----- | ---------- |
| Django HTTP requests | One span per view — method, route, status code, user ID | Always active |
| PostgreSQL (psycopg2) | One span per query with SQL commenter | `django-o11y[postgres]` |
| PostgreSQL (psycopg v3) | One span per query with SQL commenter | `django-o11y[postgres]` |
| MySQL (PyMySQL) | One span per query | Install [PyMySQL](https://pypi.org/project/PyMySQL/) directly |
| SQLite | One span per query | Install [sqlite3](https://docs.python.org/3/library/sqlite3.html) (stdlib) |
| Redis / cache | One span per cache operation | `django-o11y[redis]` |
| Celery tasks | One span per task, linked to the originating request via [W3C TraceContext](https://www.w3.org/TR/trace-context/) propagation | `django-o11y[celery]` |
| Outbound HTTP ([requests](https://requests.readthedocs.io/)) | One span per call | `django-o11y[http]` |
| Outbound HTTP ([urllib3](https://urllib3.readthedocs.io/)) | One span per call | `django-o11y[http]` |
| Outbound HTTP ([urllib](https://docs.python.org/3/library/urllib.html)) | One span per call | `django-o11y[http]` |
| Outbound HTTP ([httpx](https://www.python-httpx.org/)) | One span per call | `django-o11y[http]` |
| AWS SDK ([botocore](https://botocore.amazonaws.com/v1/documentation/api/latest/index.html)) | One span per API call — S3, SQS, SES, etc. | `django-o11y[aws]` + `TRACING.AWS_ENABLED: True` |

### Celery Tracing

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

Each task gets a trace span linked to the originating request via [W3C TraceContext](https://www.w3.org/TR/trace-context/) propagation through the broker.

[django-o11y](https://github.com/adinhodovic/django-o11y) sets `worker_send_task_events = True` and `task_send_sent_event = True` on startup so [celery-exporter](https://github.com/danihodovic/celery-exporter) receives task events without extra Celery configuration.

[django-o11y](https://github.com/adinhodovic/django-o11y) force-flushes tracing on `worker_process_shutdown` to reduce span loss in prefork workers.

```python
from celery import shared_task

from django_o11y.logging.utils import get_logger
from django_o11y.tracing.utils import set_custom_tags

logger = get_logger()

@shared_task
def process_order(order_id: int):
    set_custom_tags({"order_id": order_id})
    logger.info("order_processing_started", order_id=order_id)
    result = do_processing(order_id)
    logger.info("order_processing_completed", order_id=order_id)
    return result
```

---

## Adding context

Logs, traces, and profiles share the same context API. Use these functions anywhere in a request or task to attach extra fields:

```python
from django_o11y.logging.utils import add_log_context
from django_o11y.tracing.utils import set_custom_tags, add_span_attribute

# Logs + traces (most common)
set_custom_tags({"tenant_id": "acme", "feature": "checkout_v2"})

# Logs only
add_log_context(tenant_id="acme", checkout_variant="B")

# Span only
add_span_attribute("cart_size", len(cart.items))
```

| Function | Trace span | Logs | Use case |
| -------- | ---------- | ---- | -------- |
| `set_custom_tags()` | Yes | Yes | Business context shared across signals |
| `add_span_attribute()` | Yes | No | Technical span data |
| `add_log_context()` | No | Yes | Log-only debug info |

`RESOURCE_ATTRIBUTES` in your config are also merged into Pyroscope tags automatically, so profiles carry the same metadata as traces.

For full API docs see [Utility functions](utils.md).

---

## Multiprocess deployments

### How prometheus_client multiprocess mode works

`prometheus_client` decides whether to use multiprocess (mmap file) storage based on whether `PROMETHEUS_MULTIPROC_DIR` is set in the environment at the moment it is first imported. This means:

- `PROMETHEUS_MULTIPROC_DIR` must be a process-level environment variable set before the process starts.
- The directory it points to must already exist at that moment.
- [django-o11y](https://github.com/adinhodovic/django-o11y) does not create this directory. Create it in your entrypoint or Dockerfile.
- Each container or pod has its own filesystem, so the same path in your web and worker images is fine. They don't share files unless you explicitly mount a shared volume.

Create the directory and set the env var in your Dockerfile:

```dockerfile
RUN mkdir -p /tmp/myapp-prom-multiproc && \
    chown -R appuser:appuser /tmp/myapp-prom-multiproc
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/myapp-prom-multiproc
```

### Gunicorn

Each [Gunicorn](https://gunicorn.org/) worker writes per-PID `.db` files into that directory. The standard `/metrics` endpoint reads and aggregates them via `MultiProcessCollector`.

### Celery prefork workers

Tracing and profiling work without extra configuration beyond enabling Celery:

```python
DJANGO_O11Y = {
    "CELERY": {
        "ENABLED": True,
    }
}
```

Individual tasks are short-lived and can't serve an HTTP endpoint. [django-o11y](https://github.com/adinhodovic/django-o11y) runs the metrics HTTP server in the long-lived parent process instead. Each child writes metrics to a per-PID file; the parent reads all of them on each scrape and returns the combined result via `MultiProcessCollector`. No pushgateway required.

#### Prometheus metrics

The Celery parent process serves metrics on port `8009`. Unlike the Django web process, Celery workers don't normally expose any ports — open port `8009` on your worker hosts or containers so Prometheus can scrape it.

```python
DJANGO_O11Y = {
    "CELERY": {
        "ENABLED": True,
        "METRICS_PORT": 8009,  # default
    }
}
```

```yaml
# prometheus.yml
scrape_configs:
  - job_name: celery
    static_configs:
      - targets: ["worker-host:8009"]
```
