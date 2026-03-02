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

Every setting can be overridden with an environment variable. Custom env vars use the
`DJANGO_O11Y_<SECTION>_<KEY>` pattern. The three standard OpenTelemetry env vars are also
supported where they map naturally.

Precedence (lowest to highest):

1. Built-in defaults
2. `DJANGO_O11Y` Django settings dict
3. Environment variables

Runtime file defaults (log files) are per-project. The `<project>` suffix is derived from `OTEL_SERVICE_NAME`. If that env var is not set, django-o11y uses `django-app`.

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
| `LOGGING.COLORIZED` | bool | `True` when `DEBUG=True`, `False` otherwise | `DJANGO_O11Y_LOGGING_COLORIZED` |
| `LOGGING.RICH_EXCEPTIONS` | bool | `True` (requires `django-o11y[dev-logging]`) | `DJANGO_O11Y_LOGGING_RICH_EXCEPTIONS` |
| `LOGGING.OTLP_ENABLED` | bool | `False` | `DJANGO_O11Y_LOGGING_OTLP_ENABLED` |
| `LOGGING.OTLP_ENDPOINT` | str | `"http://localhost:4317"` | `OTEL_EXPORTER_OTLP_ENDPOINT` |
| `LOGGING.FILE_ENABLED` | bool | Same as `DEBUG` | `DJANGO_O11Y_LOGGING_FILE_ENABLED` |
| `LOGGING.FILE_PATH` | str | ``"${XDG_STATE_HOME:-~/.local/state}/django-o11y/<project>/django.log"`` | `DJANGO_O11Y_LOGGING_FILE_PATH` |

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

django-o11y skips full observability setup for non-server Django management
commands (for example `migrate`, `shell`, `tailwind start`).

Only commands in the server allowlist are treated as long-running processes and run
full startup instrumentation.

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
