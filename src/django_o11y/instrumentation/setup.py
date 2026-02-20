"""Auto-instrumentation setup for django-o11y."""

from typing import Any


def setup_instrumentation(config: dict[str, Any]) -> None:
    """
    Set up automatic instrumentation for Django and related libraries.

    This function instruments:
    - Django (requests, middleware, templates, database)
    - Psycopg2 (PostgreSQL, legacy driver)
    - Psycopg (PostgreSQL, v3 driver)
    - Redis
    - Requests library
    - urllib / urllib3
    - httpx
    - boto3/botocore (opt-in via TRACING.AWS_ENABLED)

    Args:
        config: Configuration dictionary from get_o11y_config()
    """
    from opentelemetry.instrumentation.django import DjangoInstrumentor

    DjangoInstrumentor().instrument()
    _instrument_database()
    _instrument_cache()
    _instrument_http_clients(config)


def _instrument_database() -> None:
    """Instrument database connections."""
    try:
        from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

        Psycopg2Instrumentor().instrument()
    except ImportError:
        pass  # psycopg2 not installed

    try:
        from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor

        PsycopgInstrumentor().instrument(skip_dep_check=True, enable_commenter=True)
    except ImportError:
        pass  # psycopg (v3) not installed

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


def _instrument_http_clients(config: dict[str, Any]) -> None:
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

    try:
        from opentelemetry.instrumentation.urllib import URLLibInstrumentor

        URLLibInstrumentor().instrument()
    except ImportError:
        pass  # opentelemetry-instrumentation-urllib not installed

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except ImportError:
        pass  # httpx not installed

    if config.get("TRACING", {}).get("AWS_ENABLED", False):
        try:
            from opentelemetry.instrumentation.botocore import BotocoreInstrumentor

            BotocoreInstrumentor().instrument()
        except ImportError:
            pass  # opentelemetry-instrumentation-botocore not installed
