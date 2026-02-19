"""Tests for configuration module."""


def test_get_observability_config_returns_config():
    from django_observability.conf import get_observability_config

    config = get_observability_config()

    assert config is not None
    assert isinstance(config, dict)
    assert "SERVICE_NAME" in config
    assert "TRACING" in config
    assert "LOGGING" in config


def test_get_observability_config_caches():
    from django_observability.conf import get_observability_config

    config1 = get_observability_config()
    config2 = get_observability_config()

    assert config1 is config2


def test_config_has_default_service_name():
    from django_observability.conf import get_observability_config

    config = get_observability_config()

    assert config["SERVICE_NAME"]
    assert isinstance(config["SERVICE_NAME"], str)


def test_config_tracing_defaults():
    from django_observability.conf import get_observability_config

    config = get_observability_config()

    assert "TRACING" in config
    assert "ENABLED" in config["TRACING"]
    assert "SAMPLE_RATE" in config["TRACING"]
    assert "OTLP_ENDPOINT" in config["TRACING"]


def test_config_logging_defaults():
    from django_observability.conf import get_observability_config

    config = get_observability_config()

    assert "LOGGING" in config
    assert "ENABLED" in config["LOGGING"]
    assert "FORMAT" in config["LOGGING"]
    assert "LEVEL" in config["LOGGING"]


def test_config_metrics_defaults():
    from django_observability.conf import get_observability_config

    config = get_observability_config()

    assert "METRICS" in config
    assert "PROMETHEUS_ENABLED" in config["METRICS"]
    assert "OTLP_ENABLED" not in config["METRICS"]


def test_config_celery_defaults():
    from django_observability.conf import get_observability_config

    config = get_observability_config()

    assert "CELERY" in config
    assert "ENABLED" in config["CELERY"]


def test_config_profiling_defaults():
    from django_observability.conf import get_observability_config

    config = get_observability_config()

    assert "PROFILING" in config
    assert "ENABLED" in config["PROFILING"]


def test_config_banner_defaults():
    from django_observability.conf import get_observability_config

    config = get_observability_config()

    if "BANNER" in config:
        assert "ENABLED" in config["BANNER"]
