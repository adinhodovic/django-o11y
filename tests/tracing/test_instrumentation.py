"""Tests for instrumentation setup."""

from unittest.mock import MagicMock, patch


def test_setup_instrumentation_instruments_django():
    from django_o11y.tracing.instrumentation import setup_instrumentation

    config = {"SERVICE_NAME": "test"}

    mock_inst = MagicMock()
    mock_django_module = MagicMock()
    mock_django_module.DjangoInstrumentor.return_value = mock_inst

    with (
        patch.dict(
            "sys.modules", {"opentelemetry.instrumentation.django": mock_django_module}
        ),
        patch("django_o11y.tracing.instrumentation._instrument_database"),
        patch("django_o11y.tracing.instrumentation._instrument_cache"),
        patch("django_o11y.tracing.instrumentation._instrument_celery"),
        patch("django_o11y.tracing.instrumentation._instrument_http_clients"),
    ):
        setup_instrumentation(config)

    mock_inst.instrument.assert_called_once()


def test_instrument_database_handles_import_error():
    from django_o11y.tracing.instrumentation import _instrument_database

    with patch("builtins.__import__", side_effect=ImportError("psycopg2 not found")):
        _instrument_database()


def test_instrument_cache_redis():
    from django_o11y.tracing.instrumentation import _instrument_cache

    with patch(
        "opentelemetry.instrumentation.redis.RedisInstrumentor"
    ) as mock_instrumentor:
        mock_inst = MagicMock()
        mock_instrumentor.return_value = mock_inst

        _instrument_cache()

        mock_inst.instrument.assert_called_once()


def test_instrument_cache_handles_import_error():
    from django_o11y.tracing.instrumentation import _instrument_cache

    with patch("builtins.__import__", side_effect=ImportError("redis not found")):
        _instrument_cache()


def test_instrument_http_clients_requests():
    from django_o11y.tracing.instrumentation import _instrument_http_clients

    mock_inst = MagicMock()
    mock_requests_module = MagicMock()
    mock_requests_module.RequestsInstrumentor.return_value = mock_inst

    with patch.dict(
        "sys.modules",
        {
            "opentelemetry.instrumentation.requests": mock_requests_module,
            "opentelemetry.instrumentation.urllib3": MagicMock(),
        },
    ):
        _instrument_http_clients({})

    mock_inst.instrument.assert_called_once()


def test_instrument_http_clients_handles_import_error():
    from django_o11y.tracing.instrumentation import _instrument_http_clients

    with patch("builtins.__import__", side_effect=ImportError("requests not found")):
        _instrument_http_clients({})


def test_instrument_http_clients_urllib3():
    from django_o11y.tracing.instrumentation import _instrument_http_clients

    mock_requests_inst = MagicMock()
    mock_urllib3_inst = MagicMock()
    mock_requests_module = MagicMock()
    mock_urllib3_module = MagicMock()
    mock_requests_module.RequestsInstrumentor.return_value = mock_requests_inst
    mock_urllib3_module.URLLib3Instrumentor.return_value = mock_urllib3_inst

    with patch.dict(
        "sys.modules",
        {
            "opentelemetry.instrumentation.requests": mock_requests_module,
            "opentelemetry.instrumentation.urllib3": mock_urllib3_module,
        },
    ):
        _instrument_http_clients({})

    mock_urllib3_inst.instrument.assert_called_once()


def test_instrument_celery_when_enabled():
    """CeleryInstrumentor is called when CELERY.ENABLED is True.

    This ensures the producer process (Django web) injects W3C traceparent
    headers into task messages so the worker can continue the trace rather
    than starting a new root span.
    """
    from django_o11y.tracing.instrumentation import _instrument_celery

    mock_inst = MagicMock()
    mock_celery_module = MagicMock()
    mock_celery_module.CeleryInstrumentor.return_value = mock_inst

    with patch.dict(
        "sys.modules",
        {"opentelemetry.instrumentation.celery": mock_celery_module},
    ):
        _instrument_celery({"CELERY": {"ENABLED": True}})

    mock_inst.instrument.assert_called_once()


def test_instrument_celery_skipped_when_disabled():
    """CeleryInstrumentor is not called when CELERY.ENABLED is False."""
    from django_o11y.tracing.instrumentation import _instrument_celery

    mock_inst = MagicMock()
    mock_celery_module = MagicMock()
    mock_celery_module.CeleryInstrumentor.return_value = mock_inst

    with patch.dict(
        "sys.modules",
        {"opentelemetry.instrumentation.celery": mock_celery_module},
    ):
        _instrument_celery({"CELERY": {"ENABLED": False}})
        _instrument_celery({})

    mock_inst.instrument.assert_not_called()


def test_instrument_celery_handles_import_error():
    """Missing opentelemetry-instrumentation-celery is silently ignored."""
    from django_o11y.tracing.instrumentation import _instrument_celery

    with patch("builtins.__import__", side_effect=ImportError("celery not found")):
        _instrument_celery({"CELERY": {"ENABLED": True}})
