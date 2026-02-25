"""Fork-safety for pre-fork servers (Gunicorn, uWSGI, etc.)."""

import logging
import os

from opentelemetry import trace

from django_o11y.config.setup import get_o11y_config

logger = logging.getLogger("django_o11y.fork")

_fork_handler_registered = False


def register_post_fork_handler() -> None:
    """Register tracing re-init hook to run in every forked child process."""
    global _fork_handler_registered
    if _fork_handler_registered:
        return

    if hasattr(os, "register_at_fork"):
        os.register_at_fork(after_in_child=_reinit_after_fork)
        logger.debug("django_o11y: registered post-fork tracing reinitialisation")

    _fork_handler_registered = True


def _reinit_after_fork() -> None:
    """Re-initialise tracing provider in a freshly forked worker."""
    try:
        config = get_o11y_config()

        if not config.get("TRACING", {}).get("ENABLED"):
            return

        existing = trace.get_tracer_provider()
        try:
            if hasattr(existing, "shutdown"):
                existing.shutdown()
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        from django_o11y.tracing.setup import setup_tracing

        setup_tracing(config)
        logger.debug(
            "django_o11y: tracing re-initialised after fork (pid=%s)", os.getpid()
        )

    except Exception:  # pylint: disable=broad-exception-caught
        logger.warning(
            "django_o11y: failed to re-initialise tracing after fork", exc_info=True
        )
