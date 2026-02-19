"""
Structlog configuration for Django Observability.

Based on the blog post: https://hodovi.cc/blog/django-development-and-production-logging/
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Any

import structlog

from django_o11y.logging.processors import add_open_telemetry_spans

logger = logging.getLogger("django_o11y.logging")


def setup_logging(config: dict[str, Any]) -> None:
    """Configure structlog: console or JSON format, optional OTLP, trace context."""
    logging_config = config["LOGGING"]

    logger.debug(
        "django_o11y: setting up logging",
        extra={
            "format": logging_config.get("FORMAT"),
            "level": logging_config.get("LEVEL"),
            "otlp_enabled": logging_config.get("OTLP_ENABLED"),
            "otlp_endpoint": logging_config.get("OTLP_ENDPOINT")
            if logging_config.get("OTLP_ENABLED")
            else None,
            "colorized": logging_config.get("COLORIZED"),
            "rich_exceptions": logging_config.get("RICH_EXCEPTIONS"),
        },
    )

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
        production_processors = [
            structlog.processors.dict_tracebacks,
        ]
        base_processors.extend(production_processors)

    formatter_processor = [structlog.stdlib.ProcessorFormatter.wrap_for_formatter]

    structlog.configure(
        processors=base_processors + formatter_processor,  # type: ignore[arg-type]
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _configure_python_logging(logging_config)


def _configure_python_logging(logging_config: dict[str, Any]) -> None:
    """Configure Python's logging module to work with structlog."""

    if logging_config["FORMAT"] == "console":
        formatter = {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(
                colors=logging_config["COLORIZED"],
            ),
        }
    else:
        formatter = {
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

    if logging_config.get("OTLP_ENABLED", False):
        from django_o11y.logging.otlp_handler import OTLPHandler

        handlers["otlp"] = {
            "()": OTLPHandler,
            "endpoint": logging_config["OTLP_ENDPOINT"],
        }
        logger.debug(
            "django_o11y: OTLP log exporter enabled",
            extra={"endpoint": logging_config["OTLP_ENDPOINT"]},
        )
    else:
        logger.debug("django_o11y: OTLP log exporter disabled")

    if logging_config.get("FILE_ENABLED", False):
        log_path = Path(logging_config["FILE_PATH"])
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # Always write JSON to the file so Alloy can parse it regardless of FORMAT
        handlers["file"] = {
            "class": "logging.FileHandler",
            "formatter": "json",
            "filename": str(log_path),
            "encoding": "utf-8",
        }
        logger.debug(
            "django_o11y: file log handler enabled",
            extra={"path": str(log_path)},
        )

    root_handlers = ["console"]
    if logging_config.get("OTLP_ENABLED", False):
        root_handlers.append("otlp")
    if logging_config.get("FILE_ENABLED", False):
        root_handlers.append("file")

    json_formatter = {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.processors.JSONRenderer(),
    }

    logging_dict = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": formatter,
            "json": json_formatter,
        },
        "handlers": handlers,
        "root": {
            "handlers": root_handlers,
            "level": "WARNING",
        },
        "loggers": {
            "django_o11y": {
                "level": logging_config["LEVEL"],
            },
            "django_structlog": {
                "level": logging_config["LEVEL"],
            },
            # Django Structlog request middlewares
            "django_structlog.middlewares": {
                "level": logging_config["REQUEST_LEVEL"],
            },
            # Django Structlog Celery receivers
            "django_structlog.celery": {
                "level": logging_config["CELERY_LEVEL"],
            },
            # Database logs
            "django.db.backends": {
                "level": logging_config["DATABASE_LEVEL"],
            },
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
            "werkzeug": {
                "handlers": ["null"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_dict)
