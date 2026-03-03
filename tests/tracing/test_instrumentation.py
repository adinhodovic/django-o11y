"""Tests for instrumentation setup."""

from unittest.mock import MagicMock, patch

import pytest


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

    mock_inst.instrument.assert_called_once_with(is_sql_commentor_enabled=True)


def test_setup_instrumentation_sql_commenter_enabled_by_default():
    """SQL commenter is on by default so queries carry trace context."""
    from django_o11y.tracing.instrumentation import setup_instrumentation

    config = {"SERVICE_NAME": "test", "TRACING": {}}

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

    mock_inst.instrument.assert_called_once_with(is_sql_commentor_enabled=True)


def test_setup_instrumentation_sql_commenter_can_be_disabled():
    """SQL commenter can be turned off via TRACING.SQL_COMMENTER=False."""
    from django_o11y.tracing.instrumentation import setup_instrumentation

    config = {"SERVICE_NAME": "test", "TRACING": {"SQL_COMMENTER": False}}

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

    mock_inst.instrument.assert_called_once_with(is_sql_commentor_enabled=False)


def test_instrument_cache_redis():
    from django_o11y.tracing.instrumentation import _instrument_cache

    with patch(
        "opentelemetry.instrumentation.redis.RedisInstrumentor"
    ) as mock_instrumentor:
        mock_inst = MagicMock()
        mock_instrumentor.return_value = mock_inst

        _instrument_cache()

        mock_inst.instrument.assert_called_once()


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
    mock_inst.is_instrumented_by_opentelemetry = False
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


@pytest.mark.parametrize(
    "fn_path,call_args",
    [
        ("django_o11y.tracing.instrumentation._instrument_database", []),
        ("django_o11y.tracing.instrumentation._instrument_cache", []),
        ("django_o11y.tracing.instrumentation._instrument_http_clients", [{}]),
        (
            "django_o11y.tracing.instrumentation._instrument_celery",
            [{"CELERY": {"ENABLED": True}}],
        ),
    ],
)
def test_instrumentation_handles_import_error(fn_path, call_args):
    """Each instrumentation helper silently ignores a missing optional package."""
    import importlib

    module_path, fn_name = fn_path.rsplit(".", 1)
    fn = getattr(importlib.import_module(module_path), fn_name)

    with patch("builtins.__import__", side_effect=ImportError("package not found")):
        fn(*call_args)  # must not raise
