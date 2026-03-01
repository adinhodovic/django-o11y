"""Logging setup and Celery logging signal integration."""

import importlib
import logging
import sys
from pathlib import Path
from typing import Any

import structlog

from django_o11y.logging.utils import OTLPHandler, add_open_telemetry_spans, get_logger

logger = get_logger()


class DevEventFilter(logging.Filter):
    """Filter out selected structlog events in dev console output."""

    def __init__(self, filtered_events: list[str]) -> None:
        super().__init__()
        self._filtered_events = frozenset(filtered_events)

    def filter(self, record: logging.LogRecord) -> bool:
        if not isinstance(record.msg, dict):
            return True
        return record.msg.get("event") not in self._filtered_events


# pylint: disable=too-many-locals,too-many-branches
def build_logging_dict(
    logging_config: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build and return a Django-compatible LOGGING dict wired for structlog."""
    if logging_config is None:
        from django_o11y.config.setup import get_config

        logging_config = get_config()["LOGGING"]

    assert logging_config is not None
    cfg: dict[str, Any] = logging_config

    _configure_structlog(cfg)
    use_foreign_pre_chain = cfg["FORMAT"] == "json"
    foreign_pre_chain = _build_foreign_pre_chain() if use_foreign_pre_chain else None

    if cfg["FORMAT"] == "console":
        console_renderer_kwargs: dict[str, Any] = {"colors": cfg["COLORIZED"]}
        if cfg.get("RICH_EXCEPTIONS", False):
            try:
                import rich as _rich  # noqa: F401

                console_renderer_kwargs["exception_formatter"] = (
                    structlog.dev.RichTracebackFormatter()
                )
            except ImportError:
                pass

        default_formatter: dict[str, Any] = {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(**console_renderer_kwargs),
        }
    else:
        default_formatter = {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
            "foreign_pre_chain": foreign_pre_chain,
        }

    json_formatter: dict[str, Any] = {
        "()": structlog.stdlib.ProcessorFormatter,
        "processor": structlog.processors.JSONRenderer(),
    }

    if foreign_pre_chain is not None:
        json_formatter["foreign_pre_chain"] = foreign_pre_chain

    console_handler: dict[str, Any] = {
        "class": "logging.StreamHandler",
        "formatter": "default",
        "stream": sys.stdout,
    }
    if cfg["FORMAT"] == "console":
        filtered = cfg.get("DEV_FILTERED_EVENTS") or []
        if filtered:
            console_handler["filters"] = [DevEventFilter(filtered)]

    handlers: dict[str, Any] = {
        "console": console_handler,
        "null": {
            "class": "logging.NullHandler",
        },
    }

    if cfg.get("OTLP_ENABLED", False):
        handlers["otlp"] = {
            "()": OTLPHandler,
            "endpoint": cfg["OTLP_ENDPOINT"],
        }

    if cfg.get("FILE_ENABLED", False):
        log_path = Path(cfg["FILE_PATH"])
        log_path.parent.mkdir(parents=True, exist_ok=True)
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
            "parso": {
                "level": cfg.get("PARSO_LEVEL", "WARNING"),
            },
            "botocore": {
                "level": cfg.get("AWS_LEVEL", "WARNING"),
            },
            "boto3": {
                "level": cfg.get("AWS_LEVEL", "WARNING"),
            },
            "s3transfer": {
                "level": cfg.get("AWS_LEVEL", "WARNING"),
            },
            "celery.app.trace": {
                "level": "WARNING",
            },
            "celery.worker.strategy": {
                "level": "WARNING",
            },
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


def setup_logging_for_django(config: dict) -> None:
    """Configure logging during Django startup."""
    celery_config = config.get("CELERY", {})
    if celery_config.get("ENABLED", False) and celery_config.get(
        "LOGGING_ENABLED", True
    ):
        from django.conf import settings

        if not getattr(settings, "DJANGO_STRUCTLOG_CELERY_ENABLED", False):
            settings.DJANGO_STRUCTLOG_CELERY_ENABLED = True

        try:
            importlib.import_module("django_o11y.logging.signals")
        except ImportError:
            logger.warning(
                "CELERY.ENABLED is true but Celery is not installed. "
                "Install with: pip install django-o11y[celery]"
            )

    fmt = config.get("LOGGING", {}).get("FORMAT", "console")
    logger.info("Logging configured, format=%s", fmt)


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
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


def _build_foreign_pre_chain() -> list[Any]:
    """Processors used for stdlib log records.

    These run for non-structlog loggers via ProcessorFormatter's
    ``foreign_pre_chain`` and keep enrichment parity with structlog events.
    Without this, Django/Celery/third-party stdlib logs would skip our
    processor chain and miss fields like trace_id, span_id, timestamp, and
    callsite metadata.
    """
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
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
