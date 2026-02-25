"""Tests package.

Import the Celery app when Celery is installed so shared_task uses the
configured app. Keep this import optional because Celery is an optional
dependency in this project.
"""

try:
    from tests.celery_app import app as celery_app
except ModuleNotFoundError:  # pragma: no cover - optional dependency path
    celery_app = None

__all__ = ["celery_app"]
