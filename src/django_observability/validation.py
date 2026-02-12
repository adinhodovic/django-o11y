"""Configuration validation for Django Observability."""

import logging
from typing import Any


def validate_config(config: dict[str, Any]) -> list[str]:
    """
    Validate Django Observability configuration.

    Args:
        config: Configuration dictionary from DJANGO_OBSERVABILITY setting

    Returns:
        List of error messages. Empty list if validation passes.

    Example:
        >>> config = {"TRACING": {"SAMPLE_RATE": 1.5}}
        >>> errors = validate_config(config)
        >>> errors
        ['TRACING.SAMPLE_RATE must be between 0.0 and 1.0, got 1.5']
    """
    errors = []

    tracing = config.get("TRACING", {})
    if tracing:
        errors.extend(_validate_tracing(tracing))

    logging_config = config.get("LOGGING", {})
    if logging_config:
        errors.extend(_validate_logging(logging_config))

    metrics = config.get("METRICS", {})
    if metrics:
        errors.extend(_validate_metrics(metrics))

    profiling = config.get("PROFILING", {})
    if profiling:
        errors.extend(_validate_profiling(profiling))

    return errors


def _validate_tracing(tracing: dict[str, Any]) -> list[str]:
    """Validate tracing configuration."""
    errors = []

    sample_rate = tracing.get("SAMPLE_RATE")
    if sample_rate is not None:
        if not isinstance(sample_rate, (int, float)):
            errors.append(
                f"TRACING.SAMPLE_RATE must be a number, got {type(sample_rate).__name__}"
            )
        elif not (0.0 <= sample_rate <= 1.0):
            errors.append(
                f"TRACING.SAMPLE_RATE must be between 0.0 and 1.0, got {sample_rate}"
            )

    endpoint = tracing.get("OTLP_ENDPOINT")
    if endpoint:
        errors.extend(_validate_endpoint(endpoint, "TRACING.OTLP_ENDPOINT"))

    return errors


def _validate_logging(logging_config: dict[str, Any]) -> list[str]:
    """Validate logging configuration."""
    errors = []

    log_format = logging_config.get("FORMAT")
    if log_format and log_format not in ("console", "json"):
        errors.append(f"LOGGING.FORMAT must be 'console' or 'json', got '{log_format}'")

    level_keys = ["LEVEL", "REQUEST_LEVEL", "DATABASE_LEVEL", "CELERY_LEVEL"]
    valid_levels = [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
        "NOTSET",
    ]

    for key in level_keys:
        level = logging_config.get(key)
        if level:
            level_upper = str(level).upper()
            if level_upper not in valid_levels:
                errors.append(
                    f"LOGGING.{key} must be a valid log level "
                    f"({', '.join(valid_levels)}), got '{level}'"
                )

    if logging_config.get("OTLP_ENABLED"):
        endpoint = logging_config.get("OTLP_ENDPOINT")
        if endpoint:
            errors.extend(_validate_endpoint(endpoint, "LOGGING.OTLP_ENDPOINT"))

    return errors


def _validate_metrics(metrics: dict[str, Any]) -> list[str]:
    """Validate metrics configuration."""
    errors = []

    interval = metrics.get("EXPORT_INTERVAL")
    if interval is not None:
        if not isinstance(interval, int):
            errors.append(
                f"METRICS.EXPORT_INTERVAL must be an integer (seconds), "
                f"got {type(interval).__name__}"
            )
        elif interval < 1:
            errors.append(f"METRICS.EXPORT_INTERVAL must be >= 1, got {interval}")

    if metrics.get("OTLP_ENABLED"):
        endpoint = metrics.get("OTLP_ENDPOINT")
        if endpoint:
            errors.extend(_validate_endpoint(endpoint, "METRICS.OTLP_ENDPOINT"))

    return errors


def _validate_profiling(profiling: dict[str, Any]) -> list[str]:
    """Validate profiling configuration."""
    errors = []

    url = profiling.get("PYROSCOPE_URL")
    if url:
        errors.extend(_validate_endpoint(url, "PROFILING.PYROSCOPE_URL"))

    return errors


def _validate_endpoint(endpoint: str, field_name: str) -> list[str]:
    """Validate an endpoint URL."""
    errors = []

    if not isinstance(endpoint, str):
        errors.append(f"{field_name} must be a string, got {type(endpoint).__name__}")
        return errors

    if not (endpoint.startswith("http://") or endpoint.startswith("https://")):
        errors.append(
            f"{field_name} should start with 'http://' or 'https://', got '{endpoint}'"
        )

    return errors
