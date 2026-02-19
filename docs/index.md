# Django O11y

[![Test](https://github.com/adinhodovic/django-o11y/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/adinhodovic/django-o11y/actions/workflows/ci-cd.yml)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/django-o11y.svg)](https://pypi.org/project/django-o11y/)
[![PyPI Version](https://img.shields.io/pypi/v/django-o11y.svg?style=flat)](https://pypi.org/project/django-o11y/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Zero-config observability for Django — traces, logs, metrics, and profiling wired together out of the box.

This package packages up the patterns from these blog posts into a single installable library:

- [Django Monitoring with Prometheus and Grafana](https://hodovi.cc/blog/django-monitoring-with-prometheus-and-grafana/)
- [Django Development and Production Logging](https://hodovi.cc/blog/django-development-and-production-logging/)
- [Celery Monitoring with Prometheus and Grafana](https://hodovi.cc/blog/celery-monitoring-with-prometheus-and-grafana/)

## Features

- **Distributed Tracing** — OpenTelemetry traces for requests, database queries, cache, and Celery tasks
- **Structured Logging** — Structlog with colorized dev logs, JSON production logs, and automatic trace correlation
- **Metrics** — django-prometheus for infrastructure metrics and a simple API for custom business metrics
- **Profiling** — Pyroscope continuous profiling (optional)
- **Celery** — Full observability for async tasks: tracing, structured logs, and metrics
- **Grafana Dashboards** — Pre-built dashboards from the blog posts work without modification
- **Zero config** — Sensible defaults, customizable via Django settings or environment variables

## Local development stack

Start the full observability stack with one command:

```bash
python manage.py o11y stack start
```

This starts all services via Docker Compose and automatically imports the Grafana dashboards:

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

The following dashboards from the blog posts are automatically imported:

1. [Django Overview](https://grafana.com/grafana/dashboards/17617) — Request metrics, database ops, cache hit rate
2. [Django Requests Overview](https://grafana.com/grafana/dashboards/17616) — Per-view breakdown, error rates
3. [Django Requests by View](https://grafana.com/grafana/dashboards/17613) — Detailed per-view latency analysis
4. [Celery Tasks Overview](https://grafana.com/grafana/dashboards/17509) — Task states, queue length, worker status
5. [Celery Tasks by Task](https://grafana.com/grafana/dashboards/17508) — Per-task metrics and failures

## Acknowledgments

- [OpenTelemetry Python](https://github.com/open-telemetry/opentelemetry-python)
- [Structlog](https://github.com/hynek/structlog)
- [django-structlog](https://github.com/jrobichaud/django-structlog)
- [django-prometheus](https://github.com/korfuri/django-prometheus)
- [Grafana](https://grafana.com/)
