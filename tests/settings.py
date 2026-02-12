"""Django settings for tests."""

import os

SECRET_KEY = "test-secret-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django_observability",
    "tests",
]

MIDDLEWARE = [
    "django_observability.middleware.TracingMiddleware",
    "django_structlog.middlewares.RequestMiddleware",  # Use django-structlog's middleware
    "django.middleware.common.CommonMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "test_db.sqlite3",  # File-based for e2e testing
    }
}

ROOT_URLCONF = "tests.urls"

# Django Observability configuration with sane defaults
# All features enabled by default - tests should reflect production behavior
# Use environment variables to override for specific test scenarios
DJANGO_OBSERVABILITY = {
    "SERVICE_NAME": os.getenv("OTEL_SERVICE_NAME", "test-service"),
    "ENVIRONMENT": os.getenv("ENVIRONMENT", "test"),
    "NAMESPACE": os.getenv("SERVICE_NAMESPACE", ""),
    "TRACING": {
        "ENABLED": True,
        "OTLP_ENDPOINT": os.getenv("OTLP_ENDPOINT", "http://localhost:4317"),
        "SAMPLE_RATE": float(os.getenv("OTEL_TRACE_SAMPLE_RATE", "1.0")),
        "CONSOLE_EXPORTER": False,  # Too noisy in tests
    },
    "LOGGING": {
        "ENABLED": True,
        "FORMAT": "console",  # Human-readable in tests
        "LEVEL": os.getenv("LOG_LEVEL", "WARNING"),  # Reduce noise (was INFO)
        "COLORIZED": False,
        "RICH_EXCEPTIONS": False,
        "OTLP_ENABLED": False,  # Disabled in tests - no network calls
    },
    "METRICS": {
        "PROMETHEUS_ENABLED": True,  # Enabled but won't export
        "OTLP_ENABLED": False,  # Disabled in tests - no network calls
    },
    "CELERY": {
        "ENABLED": True,  # Always instrument, even if not used in all tests
    },
    "PROFILING": {
        "ENABLED": True,  # Enabled - gracefully skips if pyroscope-io not installed
        "PYROSCOPE_URL": os.getenv("PYROSCOPE_URL", "http://localhost:4040"),
        "MODE": "push",
        "TAGS": {},
    },
    "RESOURCE_ATTRIBUTES": {
        # Additional resource attributes for testing
    },
    "CUSTOM_TAGS": {
        # Custom business tags for testing
    },
}

USE_TZ = True
