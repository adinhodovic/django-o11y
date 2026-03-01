"""Configuration setup for django-o11y."""

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from django.conf import settings

from django_o11y.utils.process import get_default_server_commands


def _bool_env(key: str, default: bool) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def _float_env(key: str, default: float) -> float:
    value = os.getenv(key)
    if value is None:
        return default
    return float(value)


def _set_str(config: dict, key: str, env: str) -> None:
    if (v := os.getenv(env)) is not None:
        config[key] = v


def _set_bool(config: dict, key: str, env: str, default: bool = False) -> None:
    if os.getenv(env) is not None:
        config[key] = _bool_env(env, default)


def _set_float(config: dict, key: str, env: str, default: float = 0.0) -> None:
    if os.getenv(env) is not None:
        config[key] = _float_env(env, default)


def get_config() -> dict[str, Any]:
    """Return merged django-o11y configuration."""
    default_sample_rate = 1.0 if settings.DEBUG else 0.01

    defaults: dict[str, Any] = {
        "SERVICE_NAME": "django-app",
        "SERVICE_VERSION": "unknown",
        "SERVICE_INSTANCE_ID": None,
        "ENVIRONMENT": "development",
        "NAMESPACE": "",
        "RESOURCE_ATTRIBUTES": {},
        "TRACING": {
            "ENABLED": False,
            "OTLP_ENDPOINT": "http://localhost:4317",
            "SAMPLE_RATE": default_sample_rate,
            "CONSOLE_EXPORTER": False,
            "AWS_ENABLED": False,
        },
        "LOGGING": {
            "FORMAT": "json" if not settings.DEBUG else "console",
            "LEVEL": "INFO",
            "REQUEST_LEVEL": "INFO",
            "DATABASE_LEVEL": "WARNING",
            "CELERY_LEVEL": "INFO",
            "PARSO_LEVEL": "WARNING",
            "AWS_LEVEL": "WARNING",
            "COLORIZED": settings.DEBUG,
            "RICH_EXCEPTIONS": True,
            "OTLP_ENABLED": False,
            "OTLP_ENDPOINT": "http://localhost:4317",
            "FILE_ENABLED": settings.DEBUG,
            "FILE_PATH": None,  # resolved below after SERVICE_NAME is known
            "DEV_FILTERED_EVENTS": ["request_started"],
        },
        "METRICS": {
            "PROMETHEUS_ENABLED": True,
            "PROMETHEUS_ENDPOINT": "/metrics",
            "EXPORT_MIGRATIONS": True,
        },
        "CELERY": {
            "ENABLED": False,
            "TRACING_ENABLED": True,
            "LOGGING_ENABLED": True,
            "METRICS_ENABLED": True,
            "METRICS_PORT": 8009,
        },
        "PROFILING": {
            "ENABLED": False,
            "PYROSCOPE_URL": "http://localhost:4040",
        },
        "STARTUP": {
            "SERVER_COMMANDS": get_default_server_commands(),
        },
    }

    user_config = getattr(settings, "DJANGO_O11Y", {})
    merged = _deep_merge(defaults, user_config)
    _apply_env_overrides(merged, default_sample_rate)

    # Resolve FILE_PATH after SERVICE_NAME is fully resolved (settings + env overrides),
    # so the directory reflects the actual service name rather than the
    #  OTEL_SERVICE_NAME env var which may not be set yet at settings import time.
    if merged["LOGGING"]["FILE_PATH"] is None:
        service_id = _slugify(merged["SERVICE_NAME"])
        runtime_base_dir = _runtime_base_dir_for(service_id)
        merged["LOGGING"]["FILE_PATH"] = str(runtime_base_dir / "django.log")

    return merged


def _apply_env_overrides(config: dict[str, Any], default_sample_rate: float) -> None:
    t, lg, m, c, p, st = (
        config["TRACING"],
        config["LOGGING"],
        config["METRICS"],
        config["CELERY"],
        config["PROFILING"],
        config["STARTUP"],
    )

    _set_str(config, "SERVICE_NAME", "OTEL_SERVICE_NAME")
    _set_str(config, "SERVICE_VERSION", "OTEL_SERVICE_VERSION")
    _set_str(config, "ENVIRONMENT", "DJANGO_O11Y_ENVIRONMENT")
    _set_str(config, "NAMESPACE", "DJANGO_O11Y_NAMESPACE")
    if (v := os.getenv("OTEL_SERVICE_INSTANCE_ID")) is not None:
        config["SERVICE_INSTANCE_ID"] = v or None

    if (v := os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")) is not None:
        t["OTLP_ENDPOINT"] = v
        lg["OTLP_ENDPOINT"] = v

    _set_bool(t, "ENABLED", "DJANGO_O11Y_TRACING_ENABLED")
    _set_float(t, "SAMPLE_RATE", "OTEL_TRACES_SAMPLER_ARG", default_sample_rate)
    _set_bool(t, "CONSOLE_EXPORTER", "DJANGO_O11Y_TRACING_CONSOLE_EXPORTER")
    _set_bool(t, "AWS_ENABLED", "DJANGO_O11Y_TRACING_AWS_ENABLED")

    _set_str(lg, "FORMAT", "DJANGO_O11Y_LOGGING_FORMAT")
    _set_str(lg, "LEVEL", "DJANGO_O11Y_LOGGING_LEVEL")
    _set_str(lg, "REQUEST_LEVEL", "DJANGO_O11Y_LOGGING_REQUEST_LEVEL")
    _set_str(lg, "DATABASE_LEVEL", "DJANGO_O11Y_LOGGING_DATABASE_LEVEL")
    _set_str(lg, "CELERY_LEVEL", "DJANGO_O11Y_LOGGING_CELERY_LEVEL")
    _set_str(lg, "PARSO_LEVEL", "DJANGO_O11Y_LOGGING_PARSO_LEVEL")
    _set_str(lg, "AWS_LEVEL", "DJANGO_O11Y_LOGGING_AWS_LEVEL")
    _set_str(lg, "FILE_PATH", "DJANGO_O11Y_LOGGING_FILE_PATH")
    _set_bool(lg, "COLORIZED", "DJANGO_O11Y_LOGGING_COLORIZED", settings.DEBUG)
    _set_bool(lg, "RICH_EXCEPTIONS", "DJANGO_O11Y_LOGGING_RICH_EXCEPTIONS", True)
    _set_bool(lg, "OTLP_ENABLED", "DJANGO_O11Y_LOGGING_OTLP_ENABLED")
    _set_bool(lg, "FILE_ENABLED", "DJANGO_O11Y_LOGGING_FILE_ENABLED", settings.DEBUG)
    if (v := os.getenv("DJANGO_O11Y_LOGGING_DEV_FILTERED_EVENTS")) is not None:
        lg["DEV_FILTERED_EVENTS"] = [e.strip() for e in v.split(",") if e.strip()]

    _set_bool(m, "PROMETHEUS_ENABLED", "DJANGO_O11Y_METRICS_PROMETHEUS_ENABLED", True)
    _set_str(m, "PROMETHEUS_ENDPOINT", "DJANGO_O11Y_METRICS_PROMETHEUS_ENDPOINT")
    _set_bool(m, "EXPORT_MIGRATIONS", "DJANGO_O11Y_METRICS_EXPORT_MIGRATIONS", True)

    _set_bool(c, "ENABLED", "DJANGO_O11Y_CELERY_ENABLED")
    _set_bool(c, "TRACING_ENABLED", "DJANGO_O11Y_CELERY_TRACING_ENABLED", True)
    _set_bool(c, "LOGGING_ENABLED", "DJANGO_O11Y_CELERY_LOGGING_ENABLED", True)
    _set_bool(c, "METRICS_ENABLED", "DJANGO_O11Y_CELERY_METRICS_ENABLED", True)
    if (v := os.getenv("DJANGO_O11Y_CELERY_METRICS_PORT")) is not None:
        c["METRICS_PORT"] = int(v)

    _set_bool(p, "ENABLED", "DJANGO_O11Y_PROFILING_ENABLED")
    _set_str(p, "PYROSCOPE_URL", "DJANGO_O11Y_PROFILING_PYROSCOPE_URL")

    if (v := os.getenv("DJANGO_O11Y_STARTUP_SERVER_COMMANDS")) is not None:
        st["SERVER_COMMANDS"] = [item.strip() for item in v.split(",") if item.strip()]


def _deep_merge(default: dict, override: dict) -> dict:
    result = default.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@lru_cache(maxsize=1)
def get_o11y_config() -> dict[str, Any]:
    """Get global o11y configuration."""
    return get_config()


def _runtime_base_dir_for(service_id: str) -> Path:
    """Return per-project XDG state dir for the given service id.

    We intentionally prefer XDG *state* storage over XDG runtime storage.
    ``XDG_RUNTIME_DIR`` is ephemeral and commonly causes ownership issues when
    bind-mounted into Docker containers (directories may be created by root).
    Logs are better treated as local state.
    """
    state_home = os.getenv("XDG_STATE_HOME")
    if state_home:
        base = Path(state_home).expanduser()
    else:
        base = Path.home() / ".local" / "state"

    return base / "django-o11y" / service_id


def _slugify(value: str) -> str:
    """Normalize string for filesystem-safe directory names."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "django-app"
