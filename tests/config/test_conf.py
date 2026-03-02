"""Tests for configuration module."""

import pytest
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


@pytest.mark.parametrize(
    "section, required_keys",
    [
        ("TRACING", ["ENABLED", "SAMPLE_RATE", "OTLP_ENDPOINT"]),
        ("LOGGING", ["FORMAT", "LEVEL"]),
        ("METRICS", ["PROMETHEUS_ENABLED"]),
        ("CELERY", ["ENABLED"]),
        ("PROFILING", ["ENABLED"]),
        ("STARTUP", ["SERVER_COMMANDS"]),
    ],
)
def test_config_section_defaults(section, required_keys):
    from django_o11y.config.setup import get_o11y_config

    config = get_o11y_config()
    assert section in config
    for key in required_keys:
        assert key in config[section]


def test_config_metrics_otlp_not_present():
    """OTLP_ENABLED must not be a top-level METRICS key (it lives under LOGGING)."""
    from django_o11y.config.setup import get_o11y_config

    config = get_o11y_config()
    assert "OTLP_ENABLED" not in config["METRICS"]


def test_config_startup_server_commands_match_defaults():
    from django_o11y.config.setup import get_o11y_config
    from django_o11y.utils.process import get_default_server_commands

    config = get_o11y_config()
    assert config["STARTUP"]["SERVER_COMMANDS"] == get_default_server_commands()


def test_config_banner_defaults():
    from django_o11y.config.setup import get_o11y_config

    config = get_o11y_config()

    if "BANNER" in config:
        assert "ENABLED" in config["BANNER"]


@pytest.mark.parametrize("debug, expected_rate", [(False, 0.01), (True, 1.0)])
@override_settings(DJANGO_O11Y={})
def test_config_tracing_sample_rate_default(monkeypatch, debug, expected_rate):
    from django_o11y.config.setup import get_config

    monkeypatch.delenv("OTEL_TRACES_SAMPLER_ARG", raising=False)
    with override_settings(DEBUG=debug):
        config = get_config()
    assert config["TRACING"]["SAMPLE_RATE"] == expected_rate


def test_env_vars_take_precedence_over_django_settings(monkeypatch):
    """Env vars must win over DJANGO_O11Y settings dict."""
    from django_o11y.config.setup import get_config

    monkeypatch.setenv("OTEL_SERVICE_NAME", "from-env")
    monkeypatch.setenv("DJANGO_O11Y_TRACING_ENABLED", "true")
    monkeypatch.setenv("DJANGO_O11Y_LOGGING_LEVEL", "DEBUG")
    monkeypatch.setenv("DJANGO_O11Y_CELERY_ENABLED", "true")
    monkeypatch.setenv("DJANGO_O11Y_PROFILING_ENABLED", "true")
    monkeypatch.setenv("DJANGO_O11Y_STARTUP_SERVER_COMMANDS", "runserver,tailwind")

    with override_settings(
        DJANGO_O11Y={
            "SERVICE_NAME": "from-settings",
            "TRACING": {"ENABLED": False},
            "LOGGING": {"LEVEL": "ERROR"},
            "CELERY": {"ENABLED": False},
            "PROFILING": {"ENABLED": False},
            "STARTUP": {"SERVER_COMMANDS": ["runserver"]},
        }
    ):
        config = get_config()

    assert config["SERVICE_NAME"] == "from-env"
    assert config["TRACING"]["ENABLED"] is True
    assert config["LOGGING"]["LEVEL"] == "DEBUG"
    assert config["CELERY"]["ENABLED"] is True
    assert config["PROFILING"]["ENABLED"] is True
    assert config["STARTUP"]["SERVER_COMMANDS"] == ["runserver", "tailwind"]


@pytest.mark.parametrize(
    "env_set, env_delete, expected_file_path",
    [
        (
            {"XDG_STATE_HOME": "/state/home", "XDG_RUNTIME_DIR": "/run/user/1000"},
            ["OTEL_SERVICE_NAME"],
            "/state/home/django-o11y/django-app/django.log",
        ),
        (
            {"XDG_STATE_HOME": "/state/home", "OTEL_SERVICE_NAME": "FindWork API"},
            [],
            "/state/home/django-o11y/findwork-api/django.log",
        ),
        (
            {"HOME": "/home/example"},
            ["XDG_STATE_HOME", "OTEL_SERVICE_NAME"],
            "/home/example/.local/state/django-o11y/django-app/django.log",
        ),
    ],
)
@override_settings(BASE_DIR="/srv/example-project", DJANGO_O11Y={})
def test_runtime_defaults_file_path(
    monkeypatch, env_set, env_delete, expected_file_path
):
    from django_o11y.config.setup import get_config

    for key, val in env_set.items():
        monkeypatch.setenv(key, val)
    for key in env_delete:
        monkeypatch.delenv(key, raising=False)

    config = get_config()
    assert config["LOGGING"]["FILE_PATH"] == expected_file_path
