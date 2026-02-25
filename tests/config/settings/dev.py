"""Dev settings for running the test project locally via Docker Compose.

Extends tests.config.settings.test with a real Redis broker, a real Celery worker process,
and JSON structured logging so you can see what production logs look like.

Usage:
    DJANGO_SETTINGS_MODULE=tests.config.settings.dev python manage.py runserver
    DJANGO_SETTINGS_MODULE=tests.config.settings.dev celery -A tests.celery_app worker -l info

Or simply:
    docker compose -f docker-compose.dev.yml up --build
"""

from django_o11y.logging.setup import build_logging_dict
from tests.config.settings.test import *  # noqa: F401,F403  # pylint: disable=wildcard-import,unused-wildcard-import

DEBUG = False

CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/0"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://redis:6379/1",
    }
}

CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False

DJANGO_O11Y = {
    **DJANGO_O11Y,  # noqa: F405
    "TRACING": {
        "ENABLED": True,
        "OTLP_ENDPOINT": "http://host.docker.internal:4317",
        "SAMPLE_RATE": 1.0,
        "CONSOLE_EXPORTER": False,
    },
    "LOGGING": {
        "FORMAT": "json",
        "LEVEL": "INFO",
        "REQUEST_LEVEL": "INFO",
        "CELERY_LEVEL": "INFO",
        "FILE_ENABLED": True,
        "FILE_PATH": "/tmp/django-o11y/django.log",
    },
    "METRICS": {
        "PROMETHEUS_ENABLED": True,
    },
    "PROFILING": {
        "ENABLED": True,
        "PYROSCOPE_URL": "http://host.docker.internal:4041",
        "TAGS": {"environment": "dev"},
    },
}

LOGGING = build_logging_dict(
    extra={
        "root": {"level": "INFO"},
        "loggers": {"tests": {"level": "INFO"}},
    }
)
