"""Tests for configuration module."""

from django.test import override_settings


def test_get_o11y_config_returns_config():
    from django_o11y.config.setup import get_o11y_config

    config = get_o11y_config()

    assert config is not None
    assert isinstance(config, dict)
    assert "SERVICE_NAME" in config
    assert "TRACING" in config
    assert "LOGGING" in config


def test_get_o11y_config_caches():
    from django_o11y.config.setup import get_o11y_config

    config1 = get_o11y_config()
    config2 = get_o11y_config()

    assert config1 is config2


def test_config_has_default_service_name():
    from django_o11y.config.setup import get_o11y_config

    config = get_o11y_config()

    assert config["SERVICE_NAME"]
    assert isinstance(config["SERVICE_NAME"], str)


def test_config_tracing_defaults():
    from django_o11y.config.setup import get_o11y_config

    config = get_o11y_config()

    assert "TRACING" in config
    assert "ENABLED" in config["TRACING"]
    assert "SAMPLE_RATE" in config["TRACING"]
    assert "OTLP_ENDPOINT" in config["TRACING"]


@override_settings(DEBUG=False, DJANGO_O11Y={})
def test_config_tracing_sample_rate_default_non_debug(monkeypatch):
    from django_o11y.config.setup import get_config

    monkeypatch.delenv("OTEL_TRACES_SAMPLER_ARG", raising=False)
    config = get_config()

    assert config["TRACING"]["SAMPLE_RATE"] == 0.01


@override_settings(DEBUG=True, DJANGO_O11Y={})
def test_config_tracing_sample_rate_default_debug(monkeypatch):
    from django_o11y.config.setup import get_config

    monkeypatch.delenv("OTEL_TRACES_SAMPLER_ARG", raising=False)
    config = get_config()

    assert config["TRACING"]["SAMPLE_RATE"] == 1.0


def test_config_logging_defaults():
    from django_o11y.config.setup import get_o11y_config

    config = get_o11y_config()

    assert "LOGGING" in config
    assert "FORMAT" in config["LOGGING"]
    assert "LEVEL" in config["LOGGING"]


def test_config_metrics_defaults():
    from django_o11y.config.setup import get_o11y_config

    config = get_o11y_config()

    assert "METRICS" in config
    assert "PROMETHEUS_ENABLED" in config["METRICS"]
    assert "OTLP_ENABLED" not in config["METRICS"]


def test_config_celery_defaults():
    from django_o11y.config.setup import get_o11y_config

    config = get_o11y_config()

    assert "CELERY" in config
    assert "ENABLED" in config["CELERY"]


def test_config_profiling_defaults():
    from django_o11y.config.setup import get_o11y_config

    config = get_o11y_config()

    assert "PROFILING" in config
    assert "ENABLED" in config["PROFILING"]


def test_config_banner_defaults():
    from django_o11y.config.setup import get_o11y_config

    config = get_o11y_config()

    if "BANNER" in config:
        assert "ENABLED" in config["BANNER"]


def test_env_vars_take_precedence_over_django_settings(monkeypatch):
    """Env vars must win over DJANGO_O11Y settings dict."""
    from django_o11y.config.setup import get_config

    monkeypatch.setenv("OTEL_SERVICE_NAME", "from-env")
    monkeypatch.setenv("DJANGO_O11Y_TRACING_ENABLED", "true")
    monkeypatch.setenv("DJANGO_O11Y_LOGGING_LEVEL", "DEBUG")
    monkeypatch.setenv("DJANGO_O11Y_CELERY_ENABLED", "true")
    monkeypatch.setenv("DJANGO_O11Y_PROFILING_ENABLED", "true")

    with override_settings(
        DJANGO_O11Y={
            "SERVICE_NAME": "from-settings",
            "TRACING": {"ENABLED": False},
            "LOGGING": {"LEVEL": "ERROR"},
            "CELERY": {"ENABLED": False},
            "PROFILING": {"ENABLED": False},
        }
    ):
        config = get_config()

    assert config["SERVICE_NAME"] == "from-env"
    assert config["TRACING"]["ENABLED"] is True
    assert config["LOGGING"]["LEVEL"] == "DEBUG"
    assert config["CELERY"]["ENABLED"] is True
    assert config["PROFILING"]["ENABLED"] is True


@override_settings(BASE_DIR="/srv/example-project", DJANGO_O11Y={})
def test_runtime_defaults_use_xdg_state_home(monkeypatch):
    from django_o11y.config.setup import get_config

    monkeypatch.setenv("XDG_STATE_HOME", "/state/home")
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)

    config = get_config()

    assert (
        config["LOGGING"]["FILE_PATH"]
        == "/state/home/django-o11y/django-app/django.log"
    )


@override_settings(BASE_DIR="/srv/example-project", DJANGO_O11Y={})
def test_runtime_defaults_use_otel_service_name(monkeypatch):
    from django_o11y.config.setup import get_config

    monkeypatch.setenv("XDG_STATE_HOME", "/state/home")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "FindWork API")

    config = get_config()

    assert (
        config["LOGGING"]["FILE_PATH"]
        == "/state/home/django-o11y/findwork-api/django.log"
    )


@override_settings(BASE_DIR="/srv/example-project", DJANGO_O11Y={})
def test_runtime_defaults_fallback_to_local_state_home(monkeypatch):
    from django_o11y.config.setup import get_config

    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setenv("HOME", "/home/example")
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)

    config = get_config()

    assert (
        config["LOGGING"]["FILE_PATH"]
        == "/home/example/.local/state/django-o11y/django-app/django.log"
    )
