# Django O11y

[![Test](https://github.com/adinhodovic/django-o11y/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/adinhodovic/django-o11y/actions/workflows/ci-cd.yml)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/django-o11y.svg)](https://pypi.org/project/django-o11y/)
[![PyPI Version](https://img.shields.io/pypi/v/django-o11y.svg?style=flat)](https://pypi.org/project/django-o11y/)
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
pip install django-o11y[all]
```

**Or choose specific features:**

| Installation Command | Includes | When to Use |
|---------------------|----------|-------------|
| `pip install django-o11y` | Core (tracing + logging) | Minimal setup |
| `pip install django-o11y[celery]` | + Celery instrumentation | Async task observability |
| `pip install django-o11y[prometheus]` | + django-prometheus | Infrastructure metrics |
| `pip install django-o11y[profiling]` | + pyroscope-io | Continuous profiling |
| `pip install django-o11y[all]` | Everything | Development & full features |

**Production recommendation:**
```bash
pip install django-o11y[celery,prometheus]
```

### Basic setup

Add to your Django settings:

```python
# settings.py
INSTALLED_APPS = [
    'django_o11y',
    # ... other apps
]

MIDDLEWARE = [
    'django_o11y.middleware.TracingMiddleware',
    'django_o11y.middleware.LoggingMiddleware',
    # ... other middleware
]
```

django-o11y will automatically:

- Set up OpenTelemetry tracing
- Configure structured logging (Structlog + OTLP)
- Instrument Django, database, cache, and HTTP clients
- Export traces and logs to `http://localhost:4317` (OTLP)

See the [Usage Guide](usage.md) for Prometheus, Celery, and database backend setup.

### Configuration

All settings are optional. See the [Configuration Reference](configuration.md) for the full list.

Quick example:

```python
# settings.py
DJANGO_O11Y = {
    'SERVICE_NAME': 'my-django-app',
    'TRACING': {
        'OTLP_ENDPOINT': 'http://localhost:4317',
        'SAMPLE_RATE': 0.1,  # 10% in prod
    },
    'LOGGING': {
        'FORMAT': 'json',
        'LEVEL': 'INFO',
    },
}
```

## Local development stack

Start the full observability stack with one command:

```bash
python manage.py o11y stack start
```

This starts all services with Docker Compose and automatically imports Grafana dashboards:

- **Grafana** (http://localhost:3000) - Pre-configured dashboards
- **Tempo** - Distributed tracing backend
- **Loki** - Log aggregation
- **Prometheus** - Metrics collection
- **Pyroscope** - Continuous profiling
- **Alloy** - OTLP receiver (port 4317)

Then start your Django app and explore in Grafana:

- **Dashboards** → Django Overview, Django Requests, Celery Tasks
- **Explore** → Tempo (view traces)
- **Explore** → Loki (view logs with trace correlation)
- Click on a log → "Tempo" button → See the full trace
- Click on a metric spike → See linked traces via exemplars

## Grafana dashboards

This package works with dashboards from the blog posts:

1. **[Django Overview](https://grafana.com/grafana/dashboards/17617)** - Request metrics, database ops, cache hit rate
2. **[Django Requests Overview](https://grafana.com/grafana/dashboards/17616)** - Per-view breakdown, error rates
3. **[Django Requests by View](https://grafana.com/grafana/dashboards/17613)** - Detailed per-view latency analysis
4. **[Celery Tasks Overview](https://grafana.com/grafana/dashboards/17509)** - Task states, queue length, worker status
5. **[Celery Tasks by Task](https://grafana.com/grafana/dashboards/17508)** - Per-task metrics and failures

## Development

```bash
# Clone repo
git clone https://github.com/adinhodovic/django-o11y
cd django-o11y

# Install with uv
uv sync --all-extras

# Run tests
uv run pytest

# Run linting
uv run ruff check .
uv run pylint src/django_o11y

# Run with tox (test matrix)
uv run tox
```

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

- [OpenTelemetry Python](https://github.com/open-telemetry/opentelemetry-python)
- [Structlog](https://github.com/hynek/structlog)
- [django-structlog](https://github.com/jrobichaud/django-structlog)
- [django-prometheus](https://github.com/korfuri/django-prometheus)
- [Grafana](https://grafana.com/)
