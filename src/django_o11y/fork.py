"""Fork-safety for pre-fork servers (Gunicorn, uWSGI, etc.).

Pre-fork servers (Gunicorn's default sync/gthread workers, uWSGI) load Django
once in a master process and then call fork() to create workers.  The
BatchSpanProcessor runs a background flush thread and OTLPSpanExporter holds a
gRPC channel — neither survives fork().  The flush thread is dead in every
worker, so spans are queued but never exported.  The gRPC channel is in an
undefined state and export calls may hang or error.

os.register_at_fork(after_in_child=...) is the correct fix: it runs in each
child *immediately* after fork(), before the worker handles any requests.  We
shut down the inherited broken provider and create a fresh one with the
worker's own pid and a new gRPC connection.

This module is deliberately standalone so it can be unit-tested without
starting a real Gunicorn server.
"""

import logging
import os

from opentelemetry import trace

from django_o11y.conf import get_o11y_config
from django_o11y.tracing.provider import setup_tracing

logger = logging.getLogger("django_o11y.fork")

_fork_handler_registered = False


def register_post_fork_handler() -> None:
    """Register _reinit_after_fork to run in every forked child process.

    Safe to call multiple times — registers only once.  Has no effect on
    platforms that do not support os.register_at_fork (Windows).
    """
    global _fork_handler_registered
    if _fork_handler_registered:
        return

    if hasattr(os, "register_at_fork"):
        os.register_at_fork(after_in_child=_reinit_after_fork)
        logger.debug("django_o11y: registered post-fork tracing reinitialisation")

    _fork_handler_registered = True


def _reinit_after_fork() -> None:
    """Re-initialise the tracing provider in a freshly forked worker.

    Called automatically by the Python runtime in every child process after
    fork().  Shuts down the broken inherited provider (dead flush thread +
    broken gRPC channel) and creates a fresh one using the child's own pid.

    Instrumentation monkey-patches (DjangoInstrumentor, etc.) survive fork
    intact and are NOT re-applied.  Only the provider — which owns threads
    and network connections — needs reinitialisation.
    """
    try:
        config = get_o11y_config()

        if not config.get("TRACING", {}).get("ENABLED"):
            return

        # Shut down the broken inherited provider gracefully.  This stops the
        # dead flush thread and closes the inherited gRPC channel.
        # get_tracer_provider() returns the API TracerProvider which has no
        # shutdown(); the real SDK provider does — call it via hasattr so mypy
        # is happy and we degrade gracefully if it's a no-op proxy.
        existing = trace.get_tracer_provider()
        try:
            if hasattr(existing, "shutdown"):
                existing.shutdown()
        except Exception:  # pylint: disable=broad-exception-caught
            pass

        # setup_tracing calls os.getpid() at call time, so the new provider's
        # Resource will carry the worker's pid — not the master's.
        setup_tracing(config)
        logger.debug(
            "django_o11y: tracing re-initialised after fork (pid=%s)", os.getpid()
        )

    except Exception:  # pylint: disable=broad-exception-caught
        logger.warning(
            "django_o11y: failed to re-initialise tracing after fork", exc_info=True
        )
