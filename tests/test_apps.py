"""Tests for Django app configuration."""

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings


def test_app_config_name():
    from django_o11y.apps import DjangoO11yConfig

    assert DjangoO11yConfig.name == "django_o11y"


def test_app_config_default_auto_field():
    from django_o11y.apps import DjangoO11yConfig

    assert DjangoO11yConfig.default_auto_field == "django.db.models.BigAutoField"


def test_configure_tracing_calls_setup_and_registers_fork_handler():
    """_configure_tracing sets up tracing in non-prefork processes."""
    from unittest.mock import patch

    from django_o11y.apps import DjangoO11yConfig

    config = {
        "TRACING": {"ENABLED": True, "OTLP_ENDPOINT": None, "CONSOLE_EXPORTER": False},
        "PROFILING": {"ENABLED": False},
        "SERVICE_NAME": "test",
        "SERVICE_INSTANCE_ID": None,
        "SERVICE_VERSION": "1.0",
        "ENVIRONMENT": "test",
        "RESOURCE_ATTRIBUTES": {},
    }

    app_config = DjangoO11yConfig("django_o11y", __import__("django_o11y"))

    with (
        patch(
            "django_o11y.celery.detection.is_celery_prefork_pool", return_value=False
        ),
        patch("django_o11y.tracing.provider.setup_tracing") as mock_setup,
        patch("django_o11y.fork.register_post_fork_handler") as mock_fork,
    ):
        app_config._configure_tracing(config)

    mock_setup.assert_called_once_with(config)
    mock_fork.assert_called_once()


def test_configure_tracing_skips_in_celery_prefork_parent():
    from unittest.mock import patch

    from django_o11y.apps import DjangoO11yConfig

    config = {
        "TRACING": {"ENABLED": True, "OTLP_ENDPOINT": None, "CONSOLE_EXPORTER": False},
        "PROFILING": {"ENABLED": False},
        "SERVICE_NAME": "test",
        "SERVICE_INSTANCE_ID": None,
        "SERVICE_VERSION": "1.0",
        "ENVIRONMENT": "test",
        "RESOURCE_ATTRIBUTES": {},
    }

    app_config = DjangoO11yConfig("django_o11y", __import__("django_o11y"))

    with (
        patch("django_o11y.celery.detection.is_celery_prefork_pool", return_value=True),
        patch("django_o11y.tracing.provider.setup_tracing") as mock_setup,
        patch("django_o11y.fork.register_post_fork_handler") as mock_fork,
    ):
        app_config._configure_tracing(config)

    mock_setup.assert_not_called()
    mock_fork.assert_not_called()


def test_configure_tracing_skips_when_disabled():
    from unittest.mock import patch

    from django_o11y.apps import DjangoO11yConfig

    config = {"TRACING": {"ENABLED": False}}

    app_config = DjangoO11yConfig("django_o11y", __import__("django_o11y"))

    with patch("django_o11y.tracing.provider.setup_tracing") as mock_setup:
        app_config._configure_tracing(config)

    mock_setup.assert_not_called()


def test_app_ready_initializes_tracing():
    from opentelemetry import trace

    from django_o11y.conf import get_o11y_config

    get_o11y_config.cache_clear()
    config = get_o11y_config()

    if config["TRACING"]["ENABLED"]:
        tracer_provider = trace.get_tracer_provider()
        assert tracer_provider is not None
        assert hasattr(tracer_provider, "resource")

        resource = tracer_provider.resource
        assert resource.attributes.get("service.name") is not None


def test_app_ready_initializes_logging():
    import structlog

    logger = structlog.get_logger()
    assert logger is not None

    bound_logger = logger.bind(test_key="test_value")
    assert bound_logger is not None


def test_app_ready_raises_on_invalid_config():
    from django_o11y.conf import get_o11y_config

    with override_settings(
        DJANGO_O11Y={"SERVICE_NAME": "test", "TRACING": {"SAMPLE_RATE": 2.0}}
    ):
        get_o11y_config.cache_clear()

        with pytest.raises(ImproperlyConfigured) as exc_info:
            get_o11y_config()
            from django_o11y.validation import validate_config

            errors = validate_config(get_o11y_config())
            if errors:
                raise ImproperlyConfigured("\n".join(errors))

        assert "SAMPLE_RATE" in str(exc_info.value)
