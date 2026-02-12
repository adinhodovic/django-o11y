"""Tests for instrumentation setup."""

import pytest
from unittest.mock import MagicMock, patch


def test_setup_instrumentation_instruments_django():
    from django_observability.instrumentation.setup import setup_instrumentation

    config = {"SERVICE_NAME": "test"}

    with patch(
        "opentelemetry.instrumentation.django.DjangoInstrumentor"
    ) as mock_instrumentor:
        mock_inst = MagicMock()
        mock_instrumentor.return_value = mock_inst

        setup_instrumentation(config)

        mock_inst.instrument.assert_called_once()


def test_instrument_database_handles_import_error():
    from django_observability.instrumentation.setup import _instrument_database

    with patch("builtins.__import__", side_effect=ImportError("psycopg2 not found")):
        _instrument_database()


def test_instrument_cache_redis():
    from django_observability.instrumentation.setup import _instrument_cache

    with patch(
        "opentelemetry.instrumentation.redis.RedisInstrumentor"
    ) as mock_instrumentor:
        mock_inst = MagicMock()
        mock_instrumentor.return_value = mock_inst

        _instrument_cache()

        mock_inst.instrument.assert_called()


def test_instrument_cache_handles_import_error():
    from django_observability.instrumentation.setup import _instrument_cache

    with patch("builtins.__import__", side_effect=ImportError("redis not found")):
        _instrument_cache()


def test_instrument_http_clients_requests():
    from django_observability.instrumentation.setup import _instrument_http_clients

    with patch(
        "opentelemetry.instrumentation.requests.RequestsInstrumentor"
    ) as mock_instrumentor:
        mock_inst = MagicMock()
        mock_instrumentor.return_value = mock_inst

        _instrument_http_clients()

        mock_inst.instrument.assert_called()


def test_instrument_http_clients_handles_import_error():
    from django_observability.instrumentation.setup import _instrument_http_clients

    with patch("builtins.__import__", side_effect=ImportError("requests not found")):
        _instrument_http_clients()


def test_instrument_http_clients_urllib3():
    from django_observability.instrumentation.setup import _instrument_http_clients

    with patch(
        "opentelemetry.instrumentation.requests.RequestsInstrumentor"
    ) as mock_requests:
        with patch(
            "opentelemetry.instrumentation.urllib3.URLLib3Instrumentor"
        ) as mock_urllib3:
            mock_requests_inst = MagicMock()
            mock_urllib3_inst = MagicMock()
            mock_requests.return_value = mock_requests_inst
            mock_urllib3.return_value = mock_urllib3_inst

            _instrument_http_clients()

            mock_urllib3_inst.instrument.assert_called()


def test_setup_instrumentation_integration():
    from django_observability.instrumentation.setup import setup_instrumentation

    config = {"SERVICE_NAME": "test"}

    with patch(
        "opentelemetry.instrumentation.django.DjangoInstrumentor"
    ) as mock_django:
        with patch(
            "django_observability.instrumentation.setup._instrument_database"
        ) as mock_db:
            with patch(
                "django_observability.instrumentation.setup._instrument_cache"
            ) as mock_cache:
                with patch(
                    "django_observability.instrumentation.setup._instrument_http_clients"
                ) as mock_http:
                    mock_django_inst = MagicMock()
                    mock_django.return_value = mock_django_inst

                    setup_instrumentation(config)

                    mock_django_inst.instrument.assert_called_once()
                    mock_db.assert_called_once()
                    mock_cache.assert_called_once()
                    mock_http.assert_called_once()
