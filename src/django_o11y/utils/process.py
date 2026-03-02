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

_RUNTIME_BINARIES = frozenset({"celery", "daphne", "gunicorn", "uvicorn"})

_PYTHON_BINARIES = frozenset(
    {
        "python",
        "python3",
        "python3.10",
        "python3.11",
        "python3.12",
        "python3.13",
    }
)

_PYTHON_MODULE_RUNTIMES = frozenset({"celery", "daphne", "gunicorn", "uvicorn"})


def get_default_server_commands() -> list[str]:
    """Return the default allowlist of long-running server commands."""
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
    """Return ``True`` for non-server ``manage.py <command>`` calls.

    This returns ``False`` for server and worker runtimes (runserver, daphne,
    uvicorn, gunicorn, celery, and similar) so they still get full
    observability setup.
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


def should_setup_observability(server_commands: Iterable[str] | None = None) -> bool:
    """Return ``True`` only for known long-running runtime processes.

    This explicit allowlist prevents one-off tooling (tests, migrations,
    shell commands, linters) from initializing full observability by accident.
    """
    argv = sys.argv
    if not argv:
        return False

    script = os.path.basename(argv[0]).lower()

    if script in ("manage.py", "django-admin", "django-admin.py"):
        if len(argv) < 2:
            return False
        command = argv[1].strip().lower()
        return command in _normalize_server_commands(server_commands)

    if script in _RUNTIME_BINARIES:
        return True

    if script in _PYTHON_BINARIES:
        for idx, arg in enumerate(argv):
            if arg == "-m" and idx + 1 < len(argv):
                module = argv[idx + 1].strip().lower()
                return module in _PYTHON_MODULE_RUNTIMES

    return False
