"""Auto-instrumentation setup for tracing-related libraries."""

from typing import Any


def setup_instrumentation(config: dict[str, Any]) -> None:
    """Set up automatic tracing instrumentation for Django and dependencies."""
    from opentelemetry.instrumentation.django import DjangoInstrumentor

    DjangoInstrumentor().instrument(
        is_sql_commentor_enabled=config.get("TRACING", {}).get("SQL_COMMENTER", True)
    )
    _instrument_database()
    _instrument_cache()
    _instrument_celery(config)
    _instrument_http_clients(config)


def _instrument_database() -> None:
    try:
        from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

        Psycopg2Instrumentor().instrument(enable_commenter=True)
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor

        PsycopgInstrumentor().instrument(skip_dep_check=True, enable_commenter=True)
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.pymysql import PyMySQLInstrumentor

        PyMySQLInstrumentor().instrument()
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor

        SQLite3Instrumentor().instrument()
    except ImportError:
        pass


def _instrument_celery(config: dict[str, Any]) -> None:
    if not config.get("CELERY", {}).get("ENABLED", False):
        return

    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        instrumentor = CeleryInstrumentor()
        if not instrumentor.is_instrumented_by_opentelemetry:
            instrumentor.instrument()
    except ImportError:
        pass


def _instrument_cache() -> None:
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()
    except ImportError:
        pass


def _instrument_http_clients(config: dict[str, Any]) -> None:
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor

        RequestsInstrumentor().instrument()
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.urllib3 import URLLib3Instrumentor

        URLLib3Instrumentor().instrument()
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.urllib import URLLibInstrumentor

        URLLibInstrumentor().instrument()
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except ImportError:
        pass

    if config.get("TRACING", {}).get("AWS_ENABLED", False):
        try:
            from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
            from opentelemetry.propagate import get_global_textmap

            BotocoreInstrumentor().instrument(propagator=get_global_textmap())
        except ImportError:
            pass
