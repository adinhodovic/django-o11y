# Django O11y

[![Test](https://github.com/adinhodovic/django-o11y/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/adinhodovic/django-o11y/actions/workflows/ci-cd.yml)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/django-o11y.svg)](https://pypi.org/project/django-o11y/)
[![PyPI Version](https://img.shields.io/pypi/v/django-o11y.svg?style=flat)](https://pypi.org/project/django-o11y/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## What Is Django O11y?

Django O11y is an opinionated, drop-in observability library for Django. It covers traces, logs, metrics, and continuous profiling — all wired together with sensible defaults and a single `DJANGO_O11Y` settings dict.

## Why Django O11y?

Production Django applications need more than just error tracking. Request latency, slow queries, background task failures, and correlated logs are all critical for diagnosing real incidents. Assembling these tools from scratch is repetitive and error-prone.

Django O11y bundles the patterns from these blog posts into a single installable package:

- [Django Monitoring with Prometheus and Grafana](https://hodovi.cc/blog/django-monitoring-with-prometheus-and-grafana/)
- [Django Development and Production Logging](https://hodovi.cc/blog/django-development-and-production-logging/)
- [Celery Monitoring with Prometheus and Grafana](https://hodovi.cc/blog/celery-monitoring-with-prometheus-and-grafana/)

## Getting Started

```bash
pip install django-o11y
```

Follow the [Usage Guide](usage.md) for full setup instructions. See the [Configuration Reference](configuration.md) for all available options.

## How It Works

Django O11y wires up four observability pillars on `AppConfig.ready()`:

- **Tracing** — OpenTelemetry `TracerProvider` with OTLP gRPC export. `TracingMiddleware` creates a root span per request; database, cache, and outbound HTTP calls are auto-instrumented.
- **Logging** — Structlog with automatic `trace_id`/`span_id` injection so every log line links back to its trace. Colorized console output in development, JSON in production.
- **Metrics** — django-prometheus instruments requests, database operations, and cache operations. A thin `counter()`/`histogram()` API is available for custom business metrics.
- **Profiling** — Optional Pyroscope integration for continuous CPU/memory profiling with tag propagation from the active trace.

All signals are correlated by `trace_id`, so you can jump from a slow request metric to its trace and then to the structured logs emitted during that trace in a single click.

## Features

- OpenTelemetry distributed traces for requests, database queries, cache operations, and Celery tasks
- Structlog structured logging with colorized dev output, JSON production format, and automatic trace correlation
- django-prometheus metrics with a simple `counter()`/`histogram()` API for custom business metrics
- Pyroscope continuous profiling (optional)
- Full Celery observability — per-task traces linked to originating requests, structured task logs, and metrics via celery-exporter
- Pre-built Grafana dashboards and alerts from django-mixin and celery-mixin
- `manage.py o11y` CLI to start/stop the local Docker Compose observability stack and validate your setup
- Sensible defaults, overridable via `DJANGO_O11Y` settings or environment variables

## Acknowledgments

- [opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python)
- [structlog](https://github.com/hynek/structlog)
- [django-structlog](https://github.com/jrobichaud/django-structlog)
- [django-prometheus](https://github.com/korfuri/django-prometheus)
- [django-mixin](https://github.com/adinhodovic/django-mixin)
- [celery-exporter](https://github.com/danihodovic/celery-exporter)
- [grafana](https://github.com/grafana/grafana)
