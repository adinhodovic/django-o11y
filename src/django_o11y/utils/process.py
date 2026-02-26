"""Process runtime helpers shared across subsystems."""

import multiprocessing
import os


def get_process_identity() -> str:
    """Return process identity details for startup diagnostics."""
    return (
        f"pid={os.getpid()} ppid={os.getppid()} "
        f"process={multiprocessing.current_process().name}"
    )
