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

Every setting can be overridden by an environment variable. All custom env vars use the
`DJANGO_O11Y_<SECTION>_<KEY>` pattern. The three standard OpenTelemetry env vars are also
honoured where they naturally map.

Precedence (lowest to highest):

1. Built-in defaults
2. `DJANGO_O11Y` Django settings dict
3. Environment variables

Runtime file defaults (log files + Prometheus multiprocess files) are per-project. Set `DJANGO_O11Y_PROJECT_ID` to control the `<project>` directory suffix explicitly.

### Core

| Setting | Type | Default | Env var |
| ------- | ---- | ------- | ------- |
| `SERVICE_NAME` | str | `"django-app"` | `OTEL_SERVICE_NAME` |
| `SERVICE_VERSION` | str | `"unknown"` | `OTEL_SERVICE_VERSION` |
| `SERVICE_INSTANCE_ID` | str | `"<hostname>:<pid>"` | `OTEL_SERVICE_INSTANCE_ID` |
| `ENVIRONMENT` | str | `"development"` | `DJANGO_O11Y_ENVIRONMENT` |
| `NAMESPACE` | str | `""` | `DJANGO_O11Y_NAMESPACE` |
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
| `LOGGING.FILE_PATH` | str | ``"${XDG_RUNTIME_DIR:-/tmp}/django-o11y/<project>/django.log"`` | `DJANGO_O11Y_LOGGING_FILE_PATH` |

### Metrics

| Setting | Type | Default | Env var |
| ------- | ---- | ------- | ------- |
| `METRICS.PROMETHEUS_ENABLED` | bool | `True` | `DJANGO_O11Y_METRICS_PROMETHEUS_ENABLED` |
| `METRICS.PROMETHEUS_ENDPOINT` | str | `"/metrics"` | `DJANGO_O11Y_METRICS_PROMETHEUS_ENDPOINT` |
| `METRICS.EXPORT_MIGRATIONS` | bool | `True` | `DJANGO_O11Y_METRICS_EXPORT_MIGRATIONS` |
| `METRICS.MULTIPROC_BASE_DIR` | str | ``"${XDG_RUNTIME_DIR:-/tmp}/django-o11y/<project>/prometheus-multiproc"`` | `DJANGO_O11Y_METRICS_MULTIPROC_BASE_DIR` |

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
    "ENVIRONMENT": "production",
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
- `deployment.environment`
- `host.name`
- `process.pid`
