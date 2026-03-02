# Django O11y

[![Test](https://github.com/adinhodovic/django-o11y/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/adinhodovic/django-o11y/actions/workflows/ci-cd.yml)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/django-o11y.svg)](https://pypi.org/project/django-o11y/)
[![PyPI Version](https://img.shields.io/pypi/v/django-o11y.svg?style=flat)](https://pypi.org/project/django-o11y/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## What is django-o11y?

Django O11y is a drop-in observability library for Django. It gives you traces, logs, metrics, and optional profiling with one `DJANGO_O11Y` settings dict.

## Why django-o11y?

In production, error tracking alone is not enough. You also need request latency, slow query visibility, background task health, and logs tied to traces. Wiring this stack by hand is repetitive and easy to get wrong.

Django O11y bundles the patterns from these blog posts into a single installable package:

- [Django Monitoring with Prometheus and Grafana](https://hodovi.cc/blog/django-monitoring-with-prometheus-and-grafana/)
- [Django Development and Production Logging](https://hodovi.cc/blog/django-development-and-production-logging/)
- [Celery Monitoring with Prometheus and Grafana](https://hodovi.cc/blog/celery-monitoring-with-prometheus-and-grafana/)

## Getting started

```bash
pip install django-o11y
```

Start with the [Usage guide](usage.md), then use the [Configuration reference](configuration.md) when you need to tune behavior.

## How it works

Django O11y wires up four observability pillars on `AppConfig.ready()`:

- **Tracing** — OpenTelemetry `TracerProvider` with OTLP gRPC export. `TracingMiddleware` creates a root span per request; database, cache, and outbound HTTP calls are auto-instrumented.
- **Logging** — Structlog with automatic `trace_id`/`span_id` injection so every log line links back to its trace. Colorized console output in development, JSON in production.
- **Metrics** — django-prometheus instruments requests, database operations, and cache operations. A thin `counter()`/`histogram()` API is available for custom business metrics.
- **Profiling** — Optional Pyroscope integration for continuous CPU/memory profiling with tag propagation from the active trace.

All signals share `trace_id`, so you can jump from a slow metric to a trace, then to logs from that same request.

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
