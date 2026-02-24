"""Tests for configuration module."""

from django.test import override_settings


def test_get_o11y_config_returns_config():
    from django_o11y.conf import get_o11y_config

    config = get_o11y_config()

    assert config is not None
    assert isinstance(config, dict)
    assert "SERVICE_NAME" in config
    assert "TRACING" in config
    assert "LOGGING" in config


def test_get_o11y_config_caches():
    from django_o11y.conf import get_o11y_config

    config1 = get_o11y_config()
    config2 = get_o11y_config()

    assert config1 is config2


def test_config_has_default_service_name():
    from django_o11y.conf import get_o11y_config

    config = get_o11y_config()

    assert config["SERVICE_NAME"]
    assert isinstance(config["SERVICE_NAME"], str)


def test_config_tracing_defaults():
    from django_o11y.conf import get_o11y_config

    config = get_o11y_config()

    assert "TRACING" in config
    assert "ENABLED" in config["TRACING"]
    assert "SAMPLE_RATE" in config["TRACING"]
    assert "OTLP_ENDPOINT" in config["TRACING"]


@override_settings(DEBUG=False, DJANGO_O11Y={})
def test_config_tracing_sample_rate_default_non_debug(monkeypatch):
    from django_o11y.conf import get_config

    monkeypatch.delenv("OTEL_TRACES_SAMPLER_ARG", raising=False)
    config = get_config()

    assert config["TRACING"]["SAMPLE_RATE"] == 0.01


@override_settings(DEBUG=True, DJANGO_O11Y={})
def test_config_tracing_sample_rate_default_debug(monkeypatch):
    from django_o11y.conf import get_config

    monkeypatch.delenv("OTEL_TRACES_SAMPLER_ARG", raising=False)
    config = get_config()

    assert config["TRACING"]["SAMPLE_RATE"] == 1.0


def test_config_logging_defaults():
    from django_o11y.conf import get_o11y_config

    config = get_o11y_config()

    assert "LOGGING" in config
    assert "FORMAT" in config["LOGGING"]
    assert "LEVEL" in config["LOGGING"]


def test_config_metrics_defaults():
    from django_o11y.conf import get_o11y_config

    config = get_o11y_config()

    assert "METRICS" in config
    assert "PROMETHEUS_ENABLED" in config["METRICS"]
    assert "OTLP_ENABLED" not in config["METRICS"]


def test_config_celery_defaults():
    from django_o11y.conf import get_o11y_config

    config = get_o11y_config()

    assert "CELERY" in config
    assert "ENABLED" in config["CELERY"]


def test_config_profiling_defaults():
    from django_o11y.conf import get_o11y_config

    config = get_o11y_config()

    assert "PROFILING" in config
    assert "ENABLED" in config["PROFILING"]


def test_config_banner_defaults():
    from django_o11y.conf import get_o11y_config

    config = get_o11y_config()

    if "BANNER" in config:
        assert "ENABLED" in config["BANNER"]
