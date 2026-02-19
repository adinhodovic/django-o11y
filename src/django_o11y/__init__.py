"""
django-o11y - Comprehensive OpenTelemetry observability for Django.

This package provides:
- Distributed tracing with OpenTelemetry
- Structured logging with Structlog + OTLP export
- Hybrid metrics (django-prometheus + OpenTelemetry)
- Celery integration
- Profiling support (Pyroscope)
"""

__version__ = "0.1.1"

default_app_config = "django_o11y.apps.DjangoO11yConfig"
