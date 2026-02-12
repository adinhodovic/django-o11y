"""Tests for Django app configuration."""

import pytest
from django.test import override_settings
from django.core.exceptions import ImproperlyConfigured


def test_app_config_name():
    from django_observability.apps import DjangoObservabilityConfig

    assert DjangoObservabilityConfig.name == "django_observability"


def test_app_config_default_auto_field():
    from django_observability.apps import DjangoObservabilityConfig

    assert (
        DjangoObservabilityConfig.default_auto_field == "django.db.models.BigAutoField"
    )


def test_app_ready_initializes_tracing():
    from opentelemetry import trace
    from django_observability.conf import get_observability_config

    get_observability_config.cache_clear()
    config = get_observability_config()

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
    from django_observability.conf import get_observability_config

    with override_settings(
        DJANGO_OBSERVABILITY={"SERVICE_NAME": "test", "TRACING": {"SAMPLE_RATE": 2.0}}
    ):
        get_observability_config.cache_clear()

        with pytest.raises(ImproperlyConfigured) as exc_info:
            get_observability_config()
            from django_observability.validation import validate_config

            errors = validate_config(get_observability_config())
            if errors:
                raise ImproperlyConfigured("\n".join(errors))

        assert "SAMPLE_RATE" in str(exc_info.value)
