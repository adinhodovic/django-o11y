"""Django settings for tests."""

SECRET_KEY = "test-secret-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django_o11y",
    "tests",
]

MIDDLEWARE = [
    "django_o11y.middleware.TracingMiddleware",
    "django_structlog.middlewares.RequestMiddleware",
    "django.middleware.common.CommonMiddleware",
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
        "TAGS": {},
    },
}

USE_TZ = True
