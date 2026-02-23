"""Configuration module for django-o11y.

Provides sensible defaults and validates user configuration from Django settings.

Environment variables follow a single consistent prefix: `DJANGO_O11Y_<SECTION>_<KEY>`.
The three OpenTelemetry spec vars are also honoured where they naturally map:

  OTEL_SERVICE_NAME              → SERVICE_NAME
  OTEL_EXPORTER_OTLP_ENDPOINT    → TRACING.OTLP_ENDPOINT, LOGGING.OTLP_ENDPOINT
  OTEL_TRACES_SAMPLER_ARG        → TRACING.SAMPLE_RATE

All other env vars use the ``DJANGO_O11Y_`` prefix, e.g.::

  DJANGO_O11Y_ENVIRONMENT=production
  DJANGO_O11Y_TRACING_ENABLED=true
  DJANGO_O11Y_LOGGING_LEVEL=WARNING
  DJANGO_O11Y_PROFILING_ENABLED=true
"""

import os
from functools import lru_cache
from typing import Any

from django.conf import settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


def _bool_env(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def _float_env(key: str, default: float) -> float:
    value = os.getenv(key)
    if value is None:
        return default
    return float(value)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def get_config() -> dict[str, Any]:
    """
    Return the merged django-o11y configuration.

    Priority (lowest → highest):
    1. Hardcoded defaults
    2. Environment variables
    3. DJANGO_O11Y settings dict
    """
    _otlp = _env("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    defaults: dict[str, Any] = {
        "SERVICE_NAME": _env("OTEL_SERVICE_NAME", "django-app"),
        "SERVICE_VERSION": _env("OTEL_SERVICE_VERSION", "unknown"),
        # None means "compute hostname:pid at tracing setup time so forked
        # workers get their own pid rather than the master's".
        # Set OTEL_SERVICE_INSTANCE_ID to fix a specific value (e.g. pod name).
        "SERVICE_INSTANCE_ID": os.getenv("OTEL_SERVICE_INSTANCE_ID") or None,
        "ENVIRONMENT": _env("DJANGO_O11Y_ENVIRONMENT", "development"),
        "NAMESPACE": _env("DJANGO_O11Y_NAMESPACE", ""),
        "RESOURCE_ATTRIBUTES": {},
        "CUSTOM_TAGS": {},
        "TRACING": {
            "ENABLED": _bool_env("DJANGO_O11Y_TRACING_ENABLED", False),
            "OTLP_ENDPOINT": _otlp,
            "SAMPLE_RATE": _float_env("OTEL_TRACES_SAMPLER_ARG", 1.0),
            "CONSOLE_EXPORTER": _bool_env(
                "DJANGO_O11Y_TRACING_CONSOLE_EXPORTER", False
            ),
            "AWS_ENABLED": _bool_env("DJANGO_O11Y_TRACING_AWS_ENABLED", False),
        },
        "LOGGING": {
            "FORMAT": _env(
                "DJANGO_O11Y_LOGGING_FORMAT",
                "json" if not settings.DEBUG else "console",
            ),
            "LEVEL": _env("DJANGO_O11Y_LOGGING_LEVEL", "INFO"),
            "REQUEST_LEVEL": _env("DJANGO_O11Y_LOGGING_REQUEST_LEVEL", "INFO"),
            "DATABASE_LEVEL": _env("DJANGO_O11Y_LOGGING_DATABASE_LEVEL", "WARNING"),
            "CELERY_LEVEL": _env("DJANGO_O11Y_LOGGING_CELERY_LEVEL", "INFO"),
            "PARSO_LEVEL": _env("DJANGO_O11Y_LOGGING_PARSO_LEVEL", "WARNING"),
            "AWS_LEVEL": _env("DJANGO_O11Y_LOGGING_AWS_LEVEL", "WARNING"),
            "COLORIZED": _bool_env("DJANGO_O11Y_LOGGING_COLORIZED", settings.DEBUG),
            "RICH_EXCEPTIONS": _bool_env("DJANGO_O11Y_LOGGING_RICH_EXCEPTIONS", True),
            "OTLP_ENABLED": _bool_env("DJANGO_O11Y_LOGGING_OTLP_ENABLED", False),
            "OTLP_ENDPOINT": _otlp,
            "FILE_ENABLED": _bool_env(
                "DJANGO_O11Y_LOGGING_FILE_ENABLED", settings.DEBUG
            ),
            "FILE_PATH": _env(
                "DJANGO_O11Y_LOGGING_FILE_PATH", "/tmp/django-o11y/django.log"
            ),
        },
        "METRICS": {
            "PROMETHEUS_ENABLED": _bool_env(
                "DJANGO_O11Y_METRICS_PROMETHEUS_ENABLED", True
            ),
            "PROMETHEUS_ENDPOINT": _env(
                "DJANGO_O11Y_METRICS_PROMETHEUS_ENDPOINT", "/metrics"
            ),
            "EXPORT_MIGRATIONS": _bool_env(
                "DJANGO_O11Y_METRICS_EXPORT_MIGRATIONS", True
            ),
        },
        "CELERY": {
            "ENABLED": _bool_env("DJANGO_O11Y_CELERY_ENABLED", False),
            "TRACING_ENABLED": _bool_env("DJANGO_O11Y_CELERY_TRACING_ENABLED", True),
            "LOGGING_ENABLED": _bool_env("DJANGO_O11Y_CELERY_LOGGING_ENABLED", True),
            "METRICS_ENABLED": _bool_env("DJANGO_O11Y_CELERY_METRICS_ENABLED", True),
        },
        "PROFILING": {
            "ENABLED": _bool_env("DJANGO_O11Y_PROFILING_ENABLED", False),
            "PYROSCOPE_URL": _env(
                "DJANGO_O11Y_PROFILING_PYROSCOPE_URL", "http://localhost:4040"
            ),
            "TAGS": {},
        },
    }

    user_config = getattr(settings, "DJANGO_O11Y", {})
    return _deep_merge(defaults, user_config)


def _deep_merge(default: dict, override: dict) -> dict:
    """Deep merge two dictionaries."""
    result = default.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@lru_cache(maxsize=1)
def get_o11y_config() -> dict[str, Any]:
    """Get the global o11y configuration (cached via lru_cache)."""
    return get_config()
