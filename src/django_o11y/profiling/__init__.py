"""Pyroscope profiling integration with proper tags."""

import os
import socket
from typing import Any

from django_o11y import __version__


def setup_profiling(config: dict[str, Any]) -> None:
    """Configure Pyroscope with standard tags (service, version, env, host, pid)."""
    profiling_config = config.get("PROFILING", {})

    if not profiling_config.get("ENABLED"):
        return

    try:
        import pyroscope

        tags = {
            "service_name": config["SERVICE_NAME"],
            "service_version": os.getenv("SERVICE_VERSION", __version__),
            "environment": config.get("ENVIRONMENT", "development"),
            "host": socket.gethostname(),
            "process_id": str(os.getpid()),
        }

        if config.get("NAMESPACE"):
            tags["service_namespace"] = config["NAMESPACE"]

        custom_tags = profiling_config.get("TAGS", {})
        if custom_tags:
            tags.update(custom_tags)

        pyroscope.configure(
            application_name=config["SERVICE_NAME"],
            server_address=profiling_config["PYROSCOPE_URL"],
            tags=tags,
        )

    except ImportError:
        pass
    except Exception:
        pass
