# Django Observability

[![Test](https://github.com/adinhodovic/django-observability/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/adinhodovic/django-observability/actions/workflows/ci-cd.yml)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/django-observability.svg)](https://pypi.org/project/django-observability/)
[![PyPI Version](https://img.shields.io/pypi/v/django-observability.svg?style=flat)](https://pypi.org/project/django-observability/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

OpenTelemetry observability for Django with traces, logs, metrics, and profiling.

This package is based on configurations from these blog posts:

- [Django Monitoring with Prometheus and Grafana](https://hodovi.cc/blog/django-monitoring-with-prometheus-and-grafana/)
- [Django Development and Production Logging](https://hodovi.cc/blog/django-development-and-production-logging/)
- [Celery Monitoring with Prometheus and Grafana](https://hodovi.cc/blog/celery-monitoring-with-prometheus-and-grafana/)

## Features

- **Distributed Tracing** - OpenTelemetry traces for requests, database, cache, and Celery tasks
- **Structured Logging** - Structlog with colorized dev logs, JSON prod logs, and OTLP export
- **Hybrid Metrics** - django-prometheus (infrastructure) + OpenTelemetry (business metrics with exemplars)
- **Profiling** - Pyroscope continuous profiling (optional)
- **Celery Integration** - Full observability for async tasks with tracing, logging, and metrics
- **Grafana Dashboards** - Pre-built dashboards from blog posts work without changes
- **Zero config** - Works with sensible defaults, customizable via Django settings
- **Trace correlation** - Automatic trace_id and span_id injection in logs

## Quick start

### Installation

**Recommended for most users:**
```bash
pip install django-observability[all]
```

**Or choose specific features:**

| Installation Command | Includes | When to Use |
|---------------------|----------|-------------|
| `pip install django-observability` | Core (tracing + logging) | Minimal setup |
| `pip install django-observability[celery]` | + Celery instrumentation | Async task observability |
| `pip install django-observability[prometheus]` | + django-prometheus | Infrastructure metrics |
| `pip install django-observability[profiling]` | + pyroscope-io | Continuous profiling |
| `pip install django-observability[all]` | Everything | Development & full features |

**Production recommendation:**
```bash
pip install django-observability[celery,prometheus]
```

### Basic setup

Add to your Django settings:

```python
# settings.py
INSTALLED_APPS = [
    'django_observability',  # Add this
    'django.contrib.admin',
    # ... other apps
]

MIDDLEWARE = [
    'django_observability.middleware.TracingMiddleware',  # Add this
    'django_observability.middleware.LoggingMiddleware',  # Add this
    # ... other middleware
]
```

Django Observability will automatically:

- Set up OpenTelemetry tracing
- Configure structured logging (Structlog + OTLP)
- Instrument Django, database, cache, and HTTP clients
- Export traces and logs to `http://localhost:4317` (OTLP)

### Configuration

Customize via Django settings (all optional):

```python
# settings.py
DJANGO_OBSERVABILITY = {
    'SERVICE_NAME': 'my-django-app',
    
    # Tracing
    'TRACING': {
        'ENABLED': True,
        'OTLP_ENDPOINT': 'http://localhost:4317',
        'SAMPLE_RATE': 1.0,  # 100% sampling (use 0.1 for 10% in prod)
    },
    
    # Logging (based on blog post)
    'LOGGING': {
        'FORMAT': 'json',  # 'console' in dev, 'json' in prod
        'LEVEL': 'INFO',
        'REQUEST_LEVEL': 'INFO',
        'DATABASE_LEVEL': 'WARNING',
        'COLORIZED': True,  # Colorized logs in dev
        'RICH_EXCEPTIONS': True,  # Beautiful exceptions in dev
        'OTLP_ENABLED': True,  # Export logs to OTLP
    },
    
    # Metrics (hybrid: django-prometheus + OpenTelemetry)
    'METRICS': {
        'PROMETHEUS_ENABLED': True,  # Expose /metrics endpoint
        'OTLP_ENABLED': False,  # Push metrics via OTLP (disabled by default)
    },
    
    # Celery integration (disabled by default, enable if using Celery)
    'CELERY': {
        'ENABLED': False,
        'TRACING_ENABLED': True,
        'LOGGING_ENABLED': True,
        'METRICS_ENABLED': True,
    },
    
    # Profiling (optional)
    'PROFILING': {
        'ENABLED': False,
        'PYROSCOPE_URL': 'http://localhost:4040',
    },
}
```

Or use environment variables:

```bash
# Service name
export OTEL_SERVICE_NAME=my-django-app

# Tracing
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_TRACES_SAMPLER_ARG=1.0

# Logging
export DJANGO_LOG_LEVEL=INFO
export DJANGO_LOG_FORMAT=json
```

## Hybrid metrics

Django Observability uses a **hybrid metrics approach**:

### Infrastructure Metrics (django-prometheus)

Uses [django-prometheus](https://github.com/korfuri/django-prometheus) for infrastructure metrics:

- Request/response metrics (req/s, latency, status codes)
- Database operations (queries/s, latency, connection pool)
- Cache hit rates
- Migration status

Existing Grafana dashboards from the blog posts work without modification.

### Business Metrics (OpenTelemetry with Exemplars)

Use OpenTelemetry for custom business metrics with trace correlation:

```python
from django_observability.metrics import counter, histogram

# Counter with labels
payment_counter = counter("payments.processed", "Total payments processed")
payment_counter.add(1, {"status": "success", "method": "card"})

# Histogram with automatic timing and exemplars (links to traces!)
payment_latency = histogram("payments.latency", "Payment processing time", "s")

with payment_latency.time({"method": "card"}):
    result = process_payment()  # This span is automatically linked as exemplar
```

Exemplars let you click on a metric spike in Grafana and jump directly to the trace that caused it.

## Structured logging

Based on the [Django Development and Production Logging](https://hodovi.cc/blog/django-development-and-production-logging/) blog post.

### Development (colorized console)

```python
import structlog

logger = structlog.get_logger(__name__)
logger.info("Payment processed", amount=100, user_id=123)
```

Output:
```
2026-02-12T10:30:45 [info     ] Payment processed    amount=100 user_id=123 [views.py:42]
```

### Production (JSON + OTLP)

```json
{
  "event": "Payment processed",
  "amount": 100,
  "user_id": 123,
  "trace_id": "a1b2c3d4e5f6g7h8",
  "span_id": "i9j0k1l2m3n4",
  "timestamp": "2026-02-12T10:30:45.123Z",
  "level": "info",
  "logger": "myapp.views",
  "filename": "views.py",
  "func_name": "process_payment",
  "lineno": 42
}
```

**Logs automatically include `trace_id` and `span_id`** - click on a log in Grafana Loki and jump to its trace in Tempo!

## Celery integration

Zero-config Celery observability. Enable it in settings:

```python
# settings.py
DJANGO_OBSERVABILITY = {
    'CELERY': {
        'ENABLED': True,  # Auto-instruments when worker starts
    },
}
```

When your Celery worker starts, observability is automatically set up via signals. No manual function calls needed!

### Manual setup (optional)

For advanced use cases or backwards compatibility:

```python
# celery_app.py
from celery import Celery
from django_observability.celery import setup_celery_observability

app = Celery('myapp')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Optional: Manual setup (auto-called via signals if CELERY.ENABLED=True)
setup_celery_observability(app)
```

### What you get

Every Celery task automatically includes:

```python
# tasks.py
import structlog

logger = structlog.get_logger(__name__)

@app.task
def process_order(order_id):
    # Automatic observability:
    # Distributed tracing span (linked to parent request if triggered by API)
    # Task lifecycle logs (received, started, succeeded/failed, retried)
    # Structured logs with trace_id and span_id
    # Task metrics (duration, success rate)
    
    logger.info("Processing order", order_id=order_id)
    return process(order_id)
```

[Celery dashboards from the blog](https://hodovi.cc/blog/celery-monitoring-with-prometheus-and-grafana/) work without modification.

### Verification

Check that Celery observability is working:

```bash
python manage.py observability check
```

## Quick local testing

Start the full observability stack with one command:

```bash
python manage.py observability stack start
```

This starts all services with Docker Compose and automatically imports Grafana dashboards:

- **Grafana** (http://localhost:3000) - Pre-configured dashboards
- **Tempo** - Distributed tracing backend
- **Loki** - Log aggregation
- **Prometheus** - Metrics collection
- **Pyroscope** - Continuous profiling
- **Alloy** - OTLP receiver (port 4317)

Then start your Django app:

```bash
python manage.py runserver
```

Generate some traffic and explore in Grafana:

- **Dashboards** → Django Overview, Django Requests, Celery Tasks
- **Explore** → Tempo (view traces)
- **Explore** → Loki (view logs with trace correlation)
- Click on a log → "Tempo" button → See the full trace
- Click on a metric spike → See linked traces via exemplars

### Custom app URL

If your app runs in Docker or on a different port:

```bash
# App in Docker network
python manage.py observability stack start --app-url django-app:8000

# App on different port
python manage.py observability stack start --app-url host.docker.internal:3000
```

## Grafana dashboards

This package works with dashboards from the blog posts:

1. **[Django Overview](https://grafana.com/grafana/dashboards/17617)** - Request metrics, database ops, cache hit rate
2. **[Django Requests Overview](https://grafana.com/grafana/dashboards/17616)** - Per-view breakdown, error rates
3. **[Django Requests by View](https://grafana.com/grafana/dashboards/17613)** - Detailed per-view latency analysis
4. **[Celery Tasks Overview](https://grafana.com/grafana/dashboards/17509)** - Task states, queue length, worker status
5. **[Celery Tasks by Task](https://grafana.com/grafana/dashboards/17508)** - Per-task metrics and failures

All dashboards are included in the demo project.

## Development

### Local development

```bash
# Clone repo
git clone https://github.com/adinhodovic/django-observability
cd django-observability

# Install with uv
uv sync --all-extras

# Run tests
uv run pytest

# Run linting
uv run ruff check .
uv run pylint src/django_observability

# Run with tox (test matrix)
uv run tox
```

### Contributing

Contributions are welcome! Please:

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Commit with [conventional commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, etc.)
4. Push and create a PR
5. CI will run tests and linting

## Verification and troubleshooting

### Health check

Verify your setup with the built-in health check command:

```bash
python manage.py observability check
```

This will:
- Check configuration is valid
- Test OTLP endpoint connectivity
- Verify required packages are installed
- Create a test trace and show how to view it in Tempo

### Common issues

#### Silent Celery instrumentation failure

**Problem:** Celery tasks aren't traced despite `CELERY.ENABLED = True`

**Solution:** Install the required package:
```bash
pip install opentelemetry-instrumentation-celery
```

The system will warn you at startup if this package is missing.

#### Configuration errors

**Problem:** Django won't start with configuration error

**Solution:** Configuration is validated at startup. Read the error message carefully:
```
ImproperlyConfigured: Django Observability configuration errors:
  • TRACING.SAMPLE_RATE must be between 0.0 and 1.0, got 1.5

Please fix these issues in your DJANGO_OBSERVABILITY setting.
```

Fix the issues in your settings and restart.

#### No traces appearing

**Problem:** Application runs but no traces in Tempo

**Check:**
1. OTLP endpoint is reachable: `python manage.py observability check`
2. Sampling rate isn't 0: Check `TRACING.SAMPLE_RATE`
3. Tracing is enabled: Check `TRACING.ENABLED`
4. OTLP receiver is running: `docker ps | grep tempo`

#### Logs not structured

**Problem:** Logs appear as plain text instead of structured JSON

**Solution:** Use `structlog.get_logger()` instead of `logging.getLogger()`:

```python
# Wrong
import logging
logger = logging.getLogger(__name__)

# Correct
import structlog
logger = structlog.get_logger(__name__)
```

### Documentation

- [Integration Guide](integration.md)
- [Configuration Reference](CONFIGURATION.md)
- [Usage Patterns](USAGE.md)
- [Report Issues](https://github.com/adinhodovic/django-observability/issues)

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

- [OpenTelemetry Python](https://github.com/open-telemetry/opentelemetry-python)
- [Structlog](https://github.com/hynek/structlog)
- [django-structlog](https://github.com/jrobichaud/django-structlog)
- [django-prometheus](https://github.com/korfuri/django-prometheus)
- [Grafana](https://grafana.com/)


