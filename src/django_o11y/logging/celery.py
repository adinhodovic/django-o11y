"""Celery worker logging bootstrap helpers."""

import os
from typing import Any

from django_o11y.logging.utils import get_logger

logger = get_logger()
_worker_receivers_by_pid: dict[int, Any] = {}


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

    # Ensure worker task lifecycle receivers are connected even when this setup
    # happens after Celery bootsteps are already in progress.
    _connect_worker_receivers_once_per_pid()


def _connect_worker_receivers_once_per_pid() -> None:
    """Connect django-structlog Celery worker receivers once per process."""
    pid = os.getpid()
    if pid in _worker_receivers_by_pid:
        return

    from django_structlog.celery.receivers import CeleryReceiver

    receiver = CeleryReceiver()
    receiver.connect_worker_signals()
    _worker_receivers_by_pid[pid] = receiver

    logger.info(
        "celery_worker_receivers_connected",
        receiver="CeleryReceiver",
        pid=pid,
    )
