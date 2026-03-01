"""Celery worker logging bootstrap helpers."""

import os
from typing import Any

from django_o11y.logging.utils import get_logger

logger = get_logger()


def setup_celery_logging(app: Any) -> None:
    """Configure Celery worker logging defaults and structlog worker step."""
    # Keep Django/structlog logging ownership in workers.
    app.conf.worker_hijack_root_logger = False
    app.conf.worker_redirect_stdouts = False

    from django_structlog.celery.steps import DjangoStructLogInitStep

    app.steps["worker"].add(DjangoStructLogInitStep)
    logger.info(
        "celery_worker_step_registered",
        step="DjangoStructLogInitStep",
        pid=os.getpid(),
    )
