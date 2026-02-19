# Configuration reference

## Basic setup

```python
# settings.py
DJANGO_O11Y = {
    "SERVICE_NAME": "my-app",
    "TRACING": {"ENABLED": True},
    "LOGGING": {"ENABLED": True},
}
```

## Options

### Core

| Setting | Type | Default | Env Var |
|---------|------|---------|---------|
| `SERVICE_NAME` | str | `"django-app"` | `OTEL_SERVICE_NAME` |
| `ENVIRONMENT` | str | `"development"` | `ENVIRONMENT` |
| `NAMESPACE` | str | `""` | `SERVICE_NAMESPACE` |
| `RESOURCE_ATTRIBUTES` | dict | `{}` | — |
| `CUSTOM_TAGS` | dict | `{}` | — |

### Tracing

| Setting | Type | Default | Env Var |
|---------|------|---------|---------|
| `TRACING.ENABLED` | bool | `False` | `DJANGO_O11Y_TRACING_ENABLED` |
| `TRACING.OTLP_ENDPOINT` | str | `"http://localhost:4317"` | `OTEL_EXPORTER_OTLP_ENDPOINT` |
| `TRACING.SAMPLE_RATE` | float | `1.0` | `OTEL_TRACES_SAMPLER_ARG` |
| `TRACING.CONSOLE_EXPORTER` | bool | `False` | `DJANGO_O11Y_CONSOLE_EXPORTER` |

### Logging

| Setting | Type | Default | Env Var |
|---------|------|---------|---------|
| `LOGGING.FORMAT` | str | `"console"` (DEBUG=True) / `"json"` (DEBUG=False) | `DJANGO_LOG_FORMAT` |
| `LOGGING.LEVEL` | str | `"INFO"` | `DJANGO_LOG_LEVEL` |
| `LOGGING.REQUEST_LEVEL` | str | `"INFO"` | `DJANGO_REQUEST_LOG_LEVEL` |
| `LOGGING.DATABASE_LEVEL` | str | `"WARNING"` | `DJANGO_DATABASE_LOG_LEVEL` |
| `LOGGING.CELERY_LEVEL` | str | `"INFO"` | `DJANGO_CELERY_LOG_LEVEL` |
| `LOGGING.COLORIZED` | bool | Same as `DEBUG` | `DJANGO_LOG_COLORIZED` |
| `LOGGING.RICH_EXCEPTIONS` | bool | Same as `DEBUG` | `DJANGO_LOG_RICH_EXCEPTIONS` |
| `LOGGING.OTLP_ENABLED` | bool | `True` | `DJANGO_O11Y_LOG_OTLP_ENABLED` |
| `LOGGING.OTLP_ENDPOINT` | str | `"http://localhost:4317"` | `OTEL_EXPORTER_OTLP_ENDPOINT` |

### Metrics

| Setting | Type | Default | Env Var |
|---------|------|---------|---------|
| `METRICS.PROMETHEUS_ENABLED` | bool | `True` | `DJANGO_O11Y_PROMETHEUS_ENABLED` |
| `METRICS.PROMETHEUS_ENDPOINT` | str | `"/metrics"` | `DJANGO_O11Y_PROMETHEUS_ENDPOINT` |

### Celery

| Setting | Type | Default | Env Var |
|---------|------|---------|---------|
| `CELERY.ENABLED` | bool | `False` | `DJANGO_O11Y_CELERY_ENABLED` |
| `CELERY.TRACING_ENABLED` | bool | `True` | `DJANGO_O11Y_CELERY_TRACING_ENABLED` |
| `CELERY.LOGGING_ENABLED` | bool | `True` | `DJANGO_O11Y_CELERY_LOGGING_ENABLED` |
| `CELERY.METRICS_ENABLED` | bool | `True` | `DJANGO_O11Y_CELERY_METRICS_ENABLED` |

### Profiling

| Setting | Type | Default | Env Var |
|---------|------|---------|---------|
| `PROFILING.ENABLED` | bool | `False` | `DJANGO_O11Y_PROFILING_ENABLED` |
| `PROFILING.PYROSCOPE_URL` | str | `"http://localhost:4040"` | `PYROSCOPE_SERVER_ADDRESS` |
| `PROFILING.TAGS` | dict | `{}` | — |

## Environment variables

```bash
export OTEL_SERVICE_NAME="my-app"
export ENVIRONMENT="production"
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
export OTEL_TRACES_SAMPLER_ARG="0.1"
export DJANGO_LOG_LEVEL="INFO"
export DJANGO_LOG_FORMAT="json"
```

## Examples

### Development

```python
DJANGO_O11Y = {
    "SERVICE_NAME": "my-app-dev",
    "TRACING": {
        "SAMPLE_RATE": 1.0,
        "CONSOLE_EXPORTER": True,  # Print traces to stdout
    },
    "LOGGING": {
        "FORMAT": "console",
        "COLORIZED": True,
        "DATABASE_LEVEL": "DEBUG",  # Log all SQL queries
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
- `deployment.environment`
- `host.name`
- `process.pid`
