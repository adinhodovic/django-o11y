"""Process runtime helpers shared across subsystems."""

import multiprocessing
import os
import sys
from collections.abc import Iterable

# Management commands that are long-running server/worker processes — these
# should go through full observability setup just like a normal process.
_SERVER_COMMANDS = frozenset(
    {
        "runserver",
        "runserver_plus",  # django-extensions
        "daphne",
        "uvicorn",
        # Celery: workers started via `manage.py celery worker` (django-celery /
        # custom management command style).  The normal `celery worker` path
        # never hits manage.py at all, so it's already safe.
        "celery",
        # Gunicorn: started via `manage.py gunicorn` (django-gunicorn package)
        # or `manage.py run_gunicorn` (old django 1.x built-in).
        "gunicorn",
        "run_gunicorn",
    }
)


def get_default_server_commands() -> list[str]:
    """Return the default long-running management command allowlist."""
    return sorted(_SERVER_COMMANDS)


def _normalize_server_commands(server_commands: Iterable[str] | None) -> set[str]:
    if server_commands is None:
        return set(_SERVER_COMMANDS)

    normalized: set[str] = set()
    for command in server_commands:
        if not isinstance(command, str):
            continue

        cleaned = command.strip().lower()
        if cleaned:
            normalized.add(cleaned)

    return normalized


def get_process_identity() -> str:
    """Return process identity details for startup diagnostics."""
    return (
        f"pid={os.getpid()} ppid={os.getppid()} "
        f"process={multiprocessing.current_process().name}"
    )


def is_management_command(server_commands: Iterable[str] | None = None) -> bool:
    """Return True when the process was started via ``manage.py <command>``.

    Returns False for:
    - Long-running server commands (``runserver``, ``daphne``, ``uvicorn``, …)
      — these need full observability initialisation.
    - Gunicorn / uWSGI / Celery worker processes — their argv looks nothing
      like a management command.
    - WSGI/ASGI apps loaded by a server (argv[0] is the server binary, not
      ``manage.py``).

    Returns True for:
    - Any ``manage.py <command>`` call where ``<command>`` is NOT a server
      command (``migrate``, ``shell``, ``check``, ``collectstatic``, etc.).

    The detection is intentionally conservative: if we cannot tell, we return
    False so that observability is not accidentally suppressed.
    """
    argv = sys.argv

    if len(argv) < 2:
        return False

    # argv[0] is the script path; it might be a relative or absolute path to
    # manage.py, or just "manage.py".  Match on basename to handle both.
    script = os.path.basename(argv[0])
    if script not in ("manage.py", "django-admin", "django-admin.py"):
        return False

    command = argv[1].lower()
    return command not in _normalize_server_commands(server_commands)
