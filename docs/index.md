# Django O11y

[![Test](https://github.com/adinhodovic/django-o11y/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/adinhodovic/django-o11y/actions/workflows/ci-cd.yml)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/django-o11y.svg)](https://pypi.org/project/django-o11y/)
[![PyPI Version](https://img.shields.io/pypi/v/django-o11y.svg?style=flat)](https://pypi.org/project/django-o11y/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Observability for Django. Traces, logs, metrics, and profiling with minimal setup.

This package bundles the patterns from these blog posts into an installable library:

- [Django Monitoring with Prometheus and Grafana](https://hodovi.cc/blog/django-monitoring-with-prometheus-and-grafana/)
- [Django Development and Production Logging](https://hodovi.cc/blog/django-development-and-production-logging/)
- [Celery Monitoring with Prometheus and Grafana](https://hodovi.cc/blog/celery-monitoring-with-prometheus-and-grafana/)

## Features

- OpenTelemetry traces for requests, database queries, cache, and Celery tasks
- Structlog with colorized dev output, JSON production logs, and automatic trace correlation
- django-prometheus for infrastructure metrics and a simple API for custom business metrics
- Pyroscope continuous profiling (optional)
- Full Celery observability: tracing, structured logs, and metrics
- Pre-built Grafana dashboards from the blog posts
- Sensible defaults, overridable via Django settings or environment variables

## Local development stack

Start the full observability stack with one command:

```bash
python manage.py o11y stack start
```

This starts all services via Docker Compose and imports the Grafana dashboards:

| Service | URL | Purpose |
|---------|-----|---------|
| Grafana | http://localhost:3000 | Dashboards (no login required) |
| Prometheus | http://localhost:9090 | Metrics |
| Tempo | http://localhost:3200 | Distributed traces |
| Loki | http://localhost:3100 | Logs |
| Pyroscope | http://localhost:4040 | Continuous profiling |
| Alloy | http://localhost:12345 | OTLP receiver + log scraping |

If your app runs in Docker or on a non-default port:

```bash
python manage.py o11y stack start --app-url host.docker.internal:8080
```

## Grafana dashboards

The following dashboards are imported automatically:

1. [Django Overview](https://grafana.com/grafana/dashboards/17617) — request metrics, database ops, cache hit rate
2. [Django Requests Overview](https://grafana.com/grafana/dashboards/17616) — per-view breakdown, error rates
3. [Django Requests by View](https://grafana.com/grafana/dashboards/17613) — per-view latency analysis
4. [Celery Tasks Overview](https://grafana.com/grafana/dashboards/17509) — task states, queue length, worker status
5. [Celery Tasks by Task](https://grafana.com/grafana/dashboards/17508) — per-task metrics and failures

## Acknowledgments

- [OpenTelemetry Python](https://github.com/open-telemetry/opentelemetry-python)
- [Structlog](https://github.com/hynek/structlog)
- [django-structlog](https://github.com/jrobichaud/django-structlog)
- [django-prometheus](https://github.com/korfuri/django-prometheus)
- [Grafana](https://grafana.com/)
