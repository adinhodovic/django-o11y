# Integration guide

## Installation

```bash
# Full install
pip install django-observability[all]

# Or minimal
pip install django-observability[celery,prometheus]
```

## Basic setup

Add to settings:

```python
# settings.py

INSTALLED_APPS = [
    "django_prometheus",      # Optional
    "django_observability",
    # ... other apps
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",  # Optional
    # ... Django middleware ...
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    
    # Add after auth middleware
    "django_observability.middleware.TracingMiddleware",
    "django_observability.middleware.LoggingMiddleware",
    
    # ... other middleware ...
    "django_prometheus.middleware.PrometheusAfterMiddleware",  # Optional
]
```

Configure:

```python
# settings.py

DJANGO_OBSERVABILITY = {
    "SERVICE_NAME": "my-app",
    "TRACING": {
        "ENABLED": True,
        "OTLP_ENDPOINT": "http://localhost:4317",
        "SAMPLE_RATE": 1.0,  # 1.0 = 100%, 0.01 = 1%
    },
    "LOGGING": {
        "ENABLED": True,
        "FORMAT": "console",  # or "json"
        "LEVEL": "INFO",
    },
}
```

## Configuration

Per-environment overrides:

```python
# settings/local.py
from .base import *

DJANGO_OBSERVABILITY["LOGGING"]["FORMAT"] = "console"
DJANGO_OBSERVABILITY["TRACING"]["SAMPLE_RATE"] = 1.0

# settings/production.py
from .base import *

DJANGO_OBSERVABILITY["LOGGING"]["FORMAT"] = "json"
DJANGO_OBSERVABILITY["TRACING"]["SAMPLE_RATE"] = 0.01
```

Database and cache backends:

```python
# Keep your existing django-prometheus backends
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

## Celery integration

Install:

```bash
pip install django-observability[celery]
```

Enable in settings:

```python
DJANGO_OBSERVABILITY = {
    # ...
    "CELERY": {
        "ENABLED": True,
    },
}

CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
```

Setup Celery app:

```python
# config/celery.py

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("myproject")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Add observability
from django_observability.celery import setup_celery_observability
setup_celery_observability(app)
```

Use in tasks:

```python
import structlog
from celery import shared_task

logger = structlog.get_logger(__name__)

@shared_task(bind=True)
def send_email(self, to: str):
    logger.info("send_email_started", to=to, task_id=self.request.id)
    # Task logic
    logger.info("send_email_completed", task_id=self.request.id)
```

## Local development

Start observability stack with Docker:

```bash
python manage.py observability stack start
```

Access services:
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090
- Tempo: http://localhost:3200

Check setup:

```bash
python manage.py observability check
```

Stop stack:

```bash
python manage.py observability stack stop
```

## Verification

Check metrics endpoint:

```bash
curl http://localhost:8000/metrics
```

Check traces:

```bash
# Generate traffic
curl http://localhost:8000/

# Query Tempo
curl 'http://localhost:3200/api/search?tags=service.name=my-app' | jq
```

Logs should include trace context:

```json
{
  "event": "request_started",
  "trace_id": "abc123...",
  "span_id": "def456...",
  "method": "GET",
  "path": "/"
}
```

## Troubleshooting

**No traces in Tempo**

Check OTLP endpoint is reachable:
```bash
curl -v http://localhost:4317
```

Check service name matches:
```bash
curl 'http://localhost:3200/api/search?tags=service.name=YOUR-APP-NAME'
```

**No metrics**

Check endpoint:
```bash
curl http://localhost:8000/metrics
```

Ensure django-prometheus is in INSTALLED_APPS.

**Database errors**

Use django-prometheus backends, not django-observability:
```python
# Correct
"ENGINE": "django_prometheus.db.backends.postgresql"

# Wrong
"ENGINE": "django_observability.db.backends.postgresql"
```

**404 errors for /debug/pprof/**

These are normal. Alloy tries to scrape Go pprof endpoints but Python apps don't expose them.

## Reference

See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for all options.

See [docs/USAGE.md](docs/USAGE.md) for usage patterns.
