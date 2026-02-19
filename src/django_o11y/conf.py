"""Configuration module for django-o11y.

Provides sensible defaults and validates user configuration from Django settings.
"""

import os
from functools import lru_cache
from typing import Any

from django.conf import settings


def get_config() -> dict[str, Any]:
    """
    Get the django-o11y configuration from Django settings.

    Returns a dictionary with all configuration merged from:
    1. Default values
    2. DJANGO_O11Y settings dict
    3. Environment variables (highest priority)
    """
    # Default configuration
    defaults = {
        "SERVICE_NAME": os.getenv(
            "OTEL_SERVICE_NAME",
            os.getenv("DJANGO_O11Y_SERVICE_NAME", "django-app"),
        ),
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "development"),
        "NAMESPACE": os.getenv("SERVICE_NAMESPACE", ""),
        "RESOURCE_ATTRIBUTES": {},
        "CUSTOM_TAGS": {},
        "TRACING": {
            "ENABLED": _get_bool_env("DJANGO_O11Y_TRACING_ENABLED", True),
            "OTLP_ENDPOINT": os.getenv(
                "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
            ),
            "SAMPLE_RATE": float(os.getenv("OTEL_TRACES_SAMPLER_ARG", "1.0")),
            "CONSOLE_EXPORTER": _get_bool_env("DJANGO_O11Y_CONSOLE_EXPORTER", False),
        },
        "LOGGING": {
            "ENABLED": _get_bool_env("DJANGO_O11Y_LOGGING_ENABLED", True),
            "FORMAT": os.getenv(
                "DJANGO_LOG_FORMAT", "json" if not settings.DEBUG else "console"
            ),
            "LEVEL": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
            "REQUEST_LEVEL": os.getenv("DJANGO_REQUEST_LOG_LEVEL", "INFO"),
            "DATABASE_LEVEL": os.getenv("DJANGO_DATABASE_LOG_LEVEL", "WARNING"),
            "CELERY_LEVEL": os.getenv("DJANGO_CELERY_LOG_LEVEL", "INFO"),
            "COLORIZED": _get_bool_env("DJANGO_LOG_COLORIZED", settings.DEBUG),
            "RICH_EXCEPTIONS": _get_bool_env(
                "DJANGO_LOG_RICH_EXCEPTIONS", settings.DEBUG
            ),
            "OTLP_ENABLED": _get_bool_env("DJANGO_O11Y_LOG_OTLP_ENABLED", False),
            "OTLP_ENDPOINT": os.getenv(
                "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
            ),
        },
        "METRICS": {
            "PROMETHEUS_ENABLED": _get_bool_env("DJANGO_O11Y_PROMETHEUS_ENABLED", True),
            "PROMETHEUS_ENDPOINT": os.getenv(
                "DJANGO_O11Y_PROMETHEUS_ENDPOINT", "/metrics"
            ),
        },
        "CELERY": {
            "ENABLED": _get_bool_env("DJANGO_O11Y_CELERY_ENABLED", False),
            "TRACING_ENABLED": _get_bool_env(
                "DJANGO_O11Y_CELERY_TRACING_ENABLED", True
            ),
            "LOGGING_ENABLED": _get_bool_env(
                "DJANGO_O11Y_CELERY_LOGGING_ENABLED", True
            ),
            "METRICS_ENABLED": _get_bool_env(
                "DJANGO_O11Y_CELERY_METRICS_ENABLED", True
            ),
        },
        "PROFILING": {
            "ENABLED": _get_bool_env("DJANGO_O11Y_PROFILING_ENABLED", False),
            "PYROSCOPE_URL": os.getenv(
                "PYROSCOPE_SERVER_ADDRESS", "http://localhost:4040"
            ),
            "MODE": os.getenv("PYROSCOPE_MODE", "push"),
            "TAGS": {},  # Custom profiling tags
        },
    }

    # Merge with user settings
    user_config = getattr(settings, "DJANGO_O11Y", {})
    config = _deep_merge(defaults, user_config)

    return config


def _get_bool_env(key: str, default: bool) -> bool:
    """Get boolean value from environment variable."""
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


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
