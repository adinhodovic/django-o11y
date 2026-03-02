# Django O11y

[![Test](https://github.com/adinhodovic/django-o11y/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/adinhodovic/django-o11y/actions/workflows/ci-cd.yml)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/django-o11y.svg)](https://pypi.org/project/django-o11y/)
[![PyPI Version](https://img.shields.io/pypi/v/django-o11y.svg?style=flat)](https://pypi.org/project/django-o11y/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Drop-in observability for Django. Install it, add a small config, and get traces, structured logs, metrics, and profiling.

## Features

- OpenTelemetry traces for requests, database queries, cache, and Celery tasks
- Structlog with colorized dev output, JSON production logs, and automatic trace correlation
- django-prometheus for infrastructure metrics and a simple API for custom business metrics
- Pyroscope continuous profiling
- Full Celery observability: tracing, structured logs, and metrics
- Pre-built Grafana dashboards
- Sensible defaults, overridable via Django settings or environment variables
- Management command to spin up a local observability stack for testing

## Background

This package bundles the patterns from these blog posts into an installable library:

- [Django Monitoring with Prometheus and Grafana](https://hodovi.cc/blog/django-monitoring-with-prometheus-and-grafana/)
- [Django Development and Production Logging](https://hodovi.cc/blog/django-development-and-production-logging/)
- [Celery Monitoring with Prometheus and Grafana](https://hodovi.cc/blog/celery-monitoring-with-prometheus-and-grafana/)

## Docs

Read the full docs at [adinhodovic.github.io/django-o11y](https://adinhodovic.github.io/django-o11y/).

- [Usage Guide](https://adinhodovic.github.io/django-o11y/usage/)
- [Configuration Reference](https://adinhodovic.github.io/django-o11y/configuration/)

## License

Apache 2.0 - see [LICENSE](LICENSE)
