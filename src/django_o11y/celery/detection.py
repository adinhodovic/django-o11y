"""Shared Celery process and pool detection helpers."""

import multiprocessing
import os
import sys
from importlib import import_module


def is_celery_prefork_pool(argv: list[str] | None = None) -> bool:
    """Return True when Celery worker is running with prefork pool."""
    args = argv if argv is not None else sys.argv

    if not args or "worker" not in args:
        return False

    cmd = os.path.basename(args[0])
    is_celery_cmd = cmd == "celery"
    is_python_module = any(
        arg == "-m" and idx + 1 < len(args) and args[idx + 1] == "celery"
        for idx, arg in enumerate(args)
    )
    if not (is_celery_cmd or is_python_module):
        return False

    for idx, arg in enumerate(args):
        if arg.startswith("--pool="):
            return arg.split("=", 1)[1] == "prefork"
        if arg in {"-P", "--pool"} and idx + 1 < len(args):
            return args[idx + 1] == "prefork"

    return True


def is_celery_fork_pool_worker() -> bool:
    """Return True when running inside a Celery prefork pool child."""
    process_name = multiprocessing.current_process().name
    if process_name.startswith("ForkPoolWorker"):
        return True

    try:
        process = import_module("billiard.process")
        return process.current_process().name.startswith("ForkPoolWorker")
    except Exception:
        return False
