"""Django settings for tests."""

import os
import tempfile

SECRET_KEY = "test-secret-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]

# Set PROMETHEUS_MULTIPROC_DIR before django_prometheus is imported so that
# prometheus_client sees the env var and the directory exists at that moment.
# django_o11y is listed first in INSTALLED_APPS for the same reason — its
# AppConfig.ready() must run before django_prometheus's.
_PROM_MULTIPROC_DIR = os.path.join(
    tempfile.gettempdir(), "django-o11y-test-prom-django"
)
os.makedirs(_PROM_MULTIPROC_DIR, exist_ok=True)
os.environ["PROMETHEUS_MULTIPROC_DIR"] = _PROM_MULTIPROC_DIR

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django_o11y",
    "django_prometheus",
    "tests",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django_o11y.tracing.middleware.TracingMiddleware",
    "django_structlog.middlewares.RequestMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "test_db.sqlite3",  # File-based for e2e testing
    }
}

ROOT_URLCONF = "tests.urls"

CELERY_BROKER_URL = "memory://"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

DJANGO_O11Y = {
    "SERVICE_NAME": "test-service",
    "ENVIRONMENT": "test",
    "TRACING": {
        "ENABLED": True,
        "OTLP_ENDPOINT": "",  # No collector in tests
        "CONSOLE_EXPORTER": False,
    },
    "LOGGING": {
        "FORMAT": "console",
        "LEVEL": "WARNING",
        "COLORIZED": False,
        "RICH_EXCEPTIONS": False,
        "OTLP_ENABLED": False,
    },
    "METRICS": {
        "PROMETHEUS_ENABLED": True,
    },
    "CELERY": {
        "ENABLED": True,
    },
    "PROFILING": {
        "ENABLED": True,  # Gracefully skips if pyroscope-io not installed
        "PYROSCOPE_URL": "http://localhost:4040",
    },
}

USE_TZ = True
