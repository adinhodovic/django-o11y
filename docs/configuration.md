# Configuration reference

## Basic setup

```python
# settings.py
DJANGO_O11Y = {
    "SERVICE_NAME": "my-app",
    "TRACING": {"ENABLED": True},
}
```

## Options

Every setting can be overridden with an environment variable. Custom env vars follow the
`DJANGO_O11Y_<SECTION>_<KEY>` pattern. Three standard [OpenTelemetry](https://opentelemetry.io/) env vars are also
recognized: `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT`, and `OTEL_TRACES_SAMPLER_ARG`.

Precedence (lowest to highest):

1. Built-in defaults
2. `DJANGO_O11Y` Django settings dict
3. Environment variables

Log file paths include a `<project>` suffix derived from `SERVICE_NAME`. If `OTEL_SERVICE_NAME` is not set, it falls back to `django-app`.

### Core

| Setting | Type | Default | Env var |
| ------- | ---- | ------- | ------- |
| `SERVICE_NAME` | str | `"django-app"` | `OTEL_SERVICE_NAME` |
| `SERVICE_VERSION` | str | `"unknown"` | `OTEL_SERVICE_VERSION` |
| `SERVICE_INSTANCE_ID` | str | `"<hostname>:<pid>"` | `OTEL_SERVICE_INSTANCE_ID` |
| `RESOURCE_ATTRIBUTES` | dict | `{}` | `OTEL_RESOURCE_ATTRIBUTES` |

### Tracing

| Setting | Type | Default | Env var |
| ------- | ---- | ------- | ------- |
| `TRACING.ENABLED` | bool | `False` | `DJANGO_O11Y_TRACING_ENABLED` |
| `TRACING.OTLP_ENDPOINT` | str | `"http://localhost:4317"` | `OTEL_EXPORTER_OTLP_ENDPOINT` |
| `TRACING.SAMPLE_RATE` | float | `1.0` (`DEBUG=True`) / `0.01` (`DEBUG=False`) | `OTEL_TRACES_SAMPLER_ARG` |
| `TRACING.CONSOLE_EXPORTER` | bool | `False` | `DJANGO_O11Y_TRACING_CONSOLE_EXPORTER` |
| `TRACING.AWS_ENABLED` | bool | `False` | `DJANGO_O11Y_TRACING_AWS_ENABLED` |

### Logging

| Setting | Type | Default | Env var |
| ------- | ---- | ------- | ------- |
| `LOGGING.FORMAT` | str | `"console"` (DEBUG=True) / `"json"` (DEBUG=False) | `DJANGO_O11Y_LOGGING_FORMAT` |
| `LOGGING.LEVEL` | str | `"INFO"` | `DJANGO_O11Y_LOGGING_LEVEL` |
| `LOGGING.REQUEST_LEVEL` | str | `"INFO"` | `DJANGO_O11Y_LOGGING_REQUEST_LEVEL` |
| `LOGGING.DATABASE_LEVEL` | str | `"WARNING"` | `DJANGO_O11Y_LOGGING_DATABASE_LEVEL` |
| `LOGGING.CELERY_LEVEL` | str | `"INFO"` | `DJANGO_O11Y_LOGGING_CELERY_LEVEL` |
| `LOGGING.PARSO_LEVEL` | str | `"WARNING"` | `DJANGO_O11Y_LOGGING_PARSO_LEVEL` |
| `LOGGING.AWS_LEVEL` | str | `"WARNING"` | `DJANGO_O11Y_LOGGING_AWS_LEVEL` |
| `LOGGING.DEV_FILTERED_EVENTS` | list[str] | `["request_started"]` | `DJANGO_O11Y_LOGGING_DEV_FILTERED_EVENTS` (comma-separated) |
| `LOGGING.COLORIZED` | bool | `True` when `DEBUG=True`, `False` otherwise | `DJANGO_O11Y_LOGGING_COLORIZED` |
| `LOGGING.RICH_EXCEPTIONS` | bool | `True` (requires `django-o11y[dev-logging]`, uses [rich](https://github.com/Textualize/rich)) | `DJANGO_O11Y_LOGGING_RICH_EXCEPTIONS` |
| `LOGGING.OTLP_ENABLED` | bool | `False` | `DJANGO_O11Y_LOGGING_OTLP_ENABLED` |
| `LOGGING.OTLP_ENDPOINT` | str | `"http://localhost:4317"` | `OTEL_EXPORTER_OTLP_ENDPOINT` |
| `LOGGING.FILE_ENABLED` | bool | Same as `DEBUG` | `DJANGO_O11Y_LOGGING_FILE_ENABLED` |
| `LOGGING.FILE_PATH` | str | ``"${XDG_STATE_HOME:-~/.local/state}/django-o11y/<project>/django.log"`` | `DJANGO_O11Y_LOGGING_FILE_PATH` |

These settings control the log level for specific loggers:

- `REQUEST_LEVEL` — [django-structlog](https://github.com/jrobichaud/django-structlog) request lifecycle events (`request_started`, `request_finished`). `INFO` by default; set to `WARNING` to suppress per-request lines in high-traffic services.
- `DATABASE_LEVEL` — Django's database backend logger. `WARNING` by default; query-level logs are high volume and the same data is already available as OTel spans.
- `CELERY_LEVEL` — Celery's internal logger. `INFO` by default; set to `WARNING` to suppress worker chatter.
- `PARSO_LEVEL` — [parso](https://parso.readthedocs.io/), the Python parser used by django-extensions and IPython. `WARNING` by default; parso emits debug output during shell startup that is not useful elsewhere.
- `AWS_LEVEL` — `botocore` and `boto3`. `WARNING` by default; AWS SDK logs at `INFO` include full request/response details that are better captured as OTel spans.

### Metrics

| Setting | Type | Default | Env var |
| ------- | ---- | ------- | ------- |
| `METRICS.PROMETHEUS_ENABLED` | bool | `True` | `DJANGO_O11Y_METRICS_PROMETHEUS_ENABLED` |
| `METRICS.PROMETHEUS_ENDPOINT` | str | `"/metrics"` | `DJANGO_O11Y_METRICS_PROMETHEUS_ENDPOINT` |
| `METRICS.EXPORT_MIGRATIONS` | bool | `True` | `DJANGO_O11Y_METRICS_EXPORT_MIGRATIONS` |

Multiprocess metrics are configured via the standard `PROMETHEUS_MULTIPROC_DIR` environment variable. Set it to a pre-existing directory in your process entrypoint before the Django process starts. See [Multiprocess deployments](usage.md#multiprocess-deployments).

### Celery

| Setting | Type | Default | Env var |
| ------- | ---- | ------- | ------- |
| `CELERY.ENABLED` | bool | `False` | `DJANGO_O11Y_CELERY_ENABLED` |
| `CELERY.TRACING_ENABLED` | bool | `True` | `DJANGO_O11Y_CELERY_TRACING_ENABLED` |
| `CELERY.LOGGING_ENABLED` | bool | `True` | `DJANGO_O11Y_CELERY_LOGGING_ENABLED` |
| `CELERY.METRICS_ENABLED` | bool | `True` | `DJANGO_O11Y_CELERY_METRICS_ENABLED` |
| `CELERY.METRICS_PORT` | int | `8009` | `DJANGO_O11Y_CELERY_METRICS_PORT` |

### Profiling

| Setting | Type | Default | Env var |
| ------- | ---- | ------- | ------- |
| `PROFILING.ENABLED` | bool | `False` | `DJANGO_O11Y_PROFILING_ENABLED` |
| `PROFILING.PYROSCOPE_URL` | str | `"http://localhost:4040"` | `DJANGO_O11Y_PROFILING_PYROSCOPE_URL` |

### Startup

[django-o11y](https://github.com/adinhodovic/django-o11y) skips full observability setup for non-server management commands like `migrate`, `shell`, and `tailwind start`. Only commands in the server allowlist get full startup instrumentation.

| Setting | Type | Default | Env var |
| ------- | ---- | ------- | ------- |
| `STARTUP.SERVER_COMMANDS` | list[str] | `['celery', 'daphne', 'gunicorn', 'run_gunicorn', 'runserver', 'runserver_plus', 'uvicorn']` | `DJANGO_O11Y_STARTUP_SERVER_COMMANDS` (comma-separated) |

## Examples

### Development

```python
DJANGO_O11Y = {
    "SERVICE_NAME": "my-app-dev",
    "TRACING": {
        "SAMPLE_RATE": 1.0,
        "CONSOLE_EXPORTER": True,
    },
    "LOGGING": {
        "FORMAT": "console",
        "COLORIZED": True,
        "DATABASE_LEVEL": "DEBUG",
    },
}
```

### Production

```python
DJANGO_O11Y = {
    "SERVICE_NAME": "my-app",
    "RESOURCE_ATTRIBUTES": {
        "deployment.environment": "production",
        "service.namespace": "web",
        "cloud.region": "eu-west-1",
    },
    "TRACING": {"SAMPLE_RATE": 0.01},
    "LOGGING": {
        "FORMAT": "json",
        "COLORIZED": False,
    },
    "CELERY": {"ENABLED": True},
}
```

## Automatic attributes

Added to all traces:

- `service.name`
- `service.version`
- `service.instance.id`
- `host.name`
- `process.pid`

Set environment and namespace through `RESOURCE_ATTRIBUTES` (or `OTEL_RESOURCE_ATTRIBUTES`), for example `deployment.environment=production,service.namespace=web`.
