"""Shared signal wiring helpers."""

from collections.abc import Callable
from typing import Any


def connect_signal(signal: Any, dispatch_uid: str) -> Callable:
    """Return a decorator that registers a signal handler."""

    def _decorator(func: Callable) -> Callable:
        signal.connect(func, weak=False, dispatch_uid=dispatch_uid)
        return func

    return _decorator
