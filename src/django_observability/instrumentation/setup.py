"""Auto-instrumentation setup for Django Observability."""

from typing import Any


def setup_instrumentation(config: dict[str, Any]) -> None:
    """
    Set up automatic instrumentation for Django and related libraries.

    This function instruments:
    - Django (requests, middleware, templates, database)
    - Psycopg2 (PostgreSQL)
    - Redis
    - Requests library
    - urllib3

    Args:
        config: Configuration dictionary from get_observability_config()
    """
    from opentelemetry.instrumentation.django import DjangoInstrumentor

    DjangoInstrumentor().instrument()
    _instrument_database()
    _instrument_cache()
    _instrument_http_clients()


def _instrument_database() -> None:
    """Instrument database connections."""
    try:
        from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

        Psycopg2Instrumentor().instrument()
    except ImportError:
        pass  # psycopg2 not installed

    try:
        from opentelemetry.instrumentation.pymysql import PyMySQLInstrumentor

        PyMySQLInstrumentor().instrument()
    except ImportError:
        pass  # pymysql not installed


def _instrument_cache() -> None:
    """Instrument cache backends."""
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()
    except ImportError:
        pass  # redis not installed


def _instrument_http_clients() -> None:
    """Instrument HTTP client libraries."""
    try:
        from opentelemetry.instrumentation.requests import RequestsInstrumentor

        RequestsInstrumentor().instrument()
    except ImportError:
        pass  # requests not installed

    try:
        from opentelemetry.instrumentation.urllib3 import URLLib3Instrumentor

        URLLib3Instrumentor().instrument()
    except ImportError:
        pass  # urllib3 not installed
