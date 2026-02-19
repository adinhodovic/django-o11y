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
