"""
Structlog configuration for Django Observability.

Based on the blog post: https://hodovi.cc/blog/django-development-and-production-logging/

Usage in settings.py:

    from django_o11y.logging.config import build_logging_dict

    LOGGING = build_logging_dict()
"""

import sys
from pathlib import Path
from typing import Any

import structlog

from django_o11y.logging.processors import add_open_telemetry_spans


def build_logging_dict(
    logging_config: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build and return a Django-compatible LOGGING dict wired up for structlog.

    Call this in settings.py and assign the result to LOGGING.

    Args:
        logging_config: The LOGGING sub-dict from DJANGO_O11Y config. When
            omitted the defaults from conf.get_config() are used, which means
            the function can be called with no arguments in settings.py before
            DJANGO_O11Y is defined.
        extra: A partial LOGGING dict to deep-merge into the result, letting
            you add or override loggers/handlers without rewriting the whole
            config. For example::

                LOGGING = build_logging_dict(extra={
                    "loggers": {"myapp": {"level": "DEBUG"}},
                })
    """
    if logging_config is None:
        from django_o11y.conf import get_config

        logging_config = get_config()["LOGGING"]

    assert logging_config is not None
    cfg: dict[str, Any] = logging_config

    _configure_structlog(cfg)

    if cfg["FORMAT"] == "console":
        console_renderer_kwargs: dict[str, Any] = {"colors": cfg["COLORIZED"]}
        if cfg.get("RICH_EXCEPTIONS", False):
            try:
                import rich as _rich  # noqa: F401

                console_renderer_kwargs["exception_formatter"] = (
                    structlog.dev.RichTracebackFormatter()
                )
            except ImportError:
                pass  # Rich not installed — silently skip

        default_formatter: dict[str, Any] = {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(**console_renderer_kwargs),
        }
    else:
        default_formatter = {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
        }

    json_formatter: dict[str, Any] = {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.processors.JSONRenderer(),
    }

    handlers: dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": sys.stdout,
        },
        "null": {
            "class": "logging.NullHandler",
        },
    }

    if cfg.get("OTLP_ENABLED", False):
        from django_o11y.logging.otlp_handler import OTLPHandler

        handlers["otlp"] = {
            "()": OTLPHandler,
            "endpoint": cfg["OTLP_ENDPOINT"],
        }

    if cfg.get("FILE_ENABLED", False):
        log_path = Path(cfg["FILE_PATH"])
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Always write JSON to the file so Alloy can parse it regardless of FORMAT
        handlers["file"] = {
            "class": "logging.FileHandler",
            "formatter": "json",
            "filename": str(log_path),
            "encoding": "utf-8",
        }

    root_handlers = ["console"]
    if cfg.get("OTLP_ENABLED", False):
        root_handlers.append("otlp")
    if cfg.get("FILE_ENABLED", False):
        root_handlers.append("file")

    result: dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": default_formatter,
            "json": json_formatter,
        },
        "handlers": handlers,
        "root": {
            "handlers": root_handlers,
            "level": "WARNING",
        },
        "loggers": {
            "django_o11y": {
                "handlers": root_handlers,
                "level": cfg["LEVEL"],
                "propagate": False,
            },
            "django_structlog": {
                "level": cfg["LEVEL"],
            },
            "django_structlog.middlewares": {
                "level": cfg["REQUEST_LEVEL"],
            },
            "django_structlog.celery": {
                "level": cfg["CELERY_LEVEL"],
            },
            "django.db.backends": {
                "level": cfg["DATABASE_LEVEL"],
            },
            # Suppress built-in access logs — django-structlog middleware handles these
            "django.server": {
                "handlers": ["null"],
                "propagate": False,
            },
            "django.request": {
                "handlers": ["null"],
                "propagate": False,
            },
            "django.channels.server": {
                "handlers": ["null"],
                "propagate": False,
            },
            # Silence debug logging in interactive shell mode
            # https://github.com/ipython/ipython/issues/10946#issuecomment-568336466
            "parso": {
                "level": cfg.get("PARSO_LEVEL", "WARNING"),
            },
            # Boto logs
            "botocore": {
                "level": cfg.get("AWS_LEVEL", "WARNING"),
            },
            "boto3": {
                "level": cfg.get("AWS_LEVEL", "WARNING"),
            },
            "s3transfer": {
                "level": cfg.get("AWS_LEVEL", "WARNING"),
            },
            # Celery's built-in task lifecycle lines ("Task x received", "succeeded in")
            # duplicate the structured events from django-structlog's CeleryReceiver.
            "celery.app.trace": {
                "level": "WARNING",
            },
            "celery.worker.strategy": {
                "level": "WARNING",
            },
            # Level set explicitly — werkzeug attaches its own ColorStreamHandler
            # at import time if the logger level is NOTSET
            "werkzeug": {
                "handlers": ["null"],
                "level": "WARNING",
                "propagate": False,
            },
        },
    }

    if extra:
        _deep_merge(result, extra)

    return result


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    """Deep-merge override into base in place."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _configure_structlog(logging_config: dict[str, Any]) -> None:
    """Configure the structlog processor chain."""
    base_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.filter_by_level,
        add_open_telemetry_spans,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        structlog.processors.CallsiteParameterAdder(
            {
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            }
        ),
    ]

    if logging_config["FORMAT"] == "json":
        base_processors.append(structlog.processors.dict_tracebacks)

    structlog.configure(
        processors=base_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],  # type: ignore[arg-type]
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
