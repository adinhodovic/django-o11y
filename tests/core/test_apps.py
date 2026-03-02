"""Tests for Django app configuration."""

from unittest.mock import patch

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from tests.conftest import make_config


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
        "RESOURCE_ATTRIBUTES": {},
    }

    app_config = DjangoO11yConfig("django_o11y", __import__("django_o11y"))

    with patch("django_o11y.tracing.setup.setup_tracing_for_django") as mock_setup:
        app_config._configure_tracing(config)

    mock_setup.assert_called_once_with(config)


def test_configure_tracing_skips_when_disabled():
    from unittest.mock import patch

    from django_o11y.apps import DjangoO11yConfig

    config = {"TRACING": {"ENABLED": False}}

    app_config = DjangoO11yConfig("django_o11y", __import__("django_o11y"))

    with patch("django_o11y.tracing.setup.setup_tracing_for_django") as mock_setup:
        app_config._configure_tracing(config)

    mock_setup.assert_called_once_with(config)


def test_app_ready_initializes_tracing():
    from opentelemetry import trace

    from django_o11y.config.setup import get_o11y_config

    get_o11y_config.cache_clear()
    config = get_o11y_config()

    if config["TRACING"]["ENABLED"]:
        tracer_provider = trace.get_tracer_provider()
        assert tracer_provider is not None


def test_app_ready_initializes_logging():
    import structlog

    logger = structlog.get_logger()
    assert logger is not None

    bound_logger = logger.bind(test_key="test_value")
    assert bound_logger is not None


def test_app_ready_skips_o11y_for_non_runtime_processes_by_default():
    from unittest.mock import patch

    from django_o11y.apps import DjangoO11yConfig

    config = make_config()
    app_config = DjangoO11yConfig("django_o11y", __import__("django_o11y"))

    with (
        patch("django_o11y.apps.get_o11y_config", return_value=config),
        patch("django_o11y.apps.should_setup_observability", return_value=False),
        patch("django_o11y.apps.validate_config") as mock_validate,
        patch.object(app_config, "_configure_tracing") as mock_tracing,
        patch.object(app_config, "_configure_logging") as mock_logging,
        patch.object(app_config, "_configure_metrics") as mock_metrics,
        patch.object(app_config, "_configure_profiling") as mock_profiling,
    ):
        app_config.ready()

    mock_validate.assert_not_called()
    mock_tracing.assert_not_called()
    mock_logging.assert_not_called()
    mock_metrics.assert_not_called()
    mock_profiling.assert_not_called()


def test_app_ready_respects_configured_server_command_allowlist():
    from unittest.mock import patch

    from django_o11y.apps import DjangoO11yConfig

    config = make_config({"STARTUP": {"SERVER_COMMANDS": ["runserver", "tailwind"]}})
    app_config = DjangoO11yConfig("django_o11y", __import__("django_o11y"))

    with (
        patch("django_o11y.apps.get_o11y_config", return_value=config),
        patch(
            "django_o11y.apps.should_setup_observability", return_value=True
        ) as mock_check,
        patch("django_o11y.apps.validate_config", return_value=[]),
        patch.object(app_config, "_configure_tracing") as mock_tracing,
        patch.object(app_config, "_configure_logging") as mock_logging,
        patch.object(app_config, "_configure_metrics") as mock_metrics,
        patch.object(app_config, "_configure_profiling") as mock_profiling,
    ):
        app_config.ready()

    mock_check.assert_called_once_with(server_commands=["runserver", "tailwind"])
    mock_tracing.assert_called_once_with(config)
    mock_logging.assert_called_once_with(config)
    mock_metrics.assert_called_once_with(config)
    mock_profiling.assert_called_once_with(config)


def test_app_ready_raises_on_invalid_config():
    from django_o11y.config.setup import get_o11y_config

    with override_settings(
        DJANGO_O11Y={"SERVICE_NAME": "test", "TRACING": {"SAMPLE_RATE": 2.0}}
    ):
        get_o11y_config.cache_clear()

        with pytest.raises(ImproperlyConfigured) as exc_info:
            get_o11y_config()
            from django_o11y.config.utils import validate_config

            errors = validate_config(get_o11y_config())
            if errors:
                raise ImproperlyConfigured("\n".join(errors))

        assert "SAMPLE_RATE" in str(exc_info.value)


@pytest.mark.parametrize(
    "resolve_raises, warning_called", [(True, True), (False, False)]
)
def test_configure_metrics_warning(resolve_raises, warning_called):
    from django.urls import Resolver404

    from django_o11y.apps import DjangoO11yConfig

    config = make_config(
        {"METRICS": {"PROMETHEUS_ENABLED": True, "PROMETHEUS_ENDPOINT": "/metrics"}}
    )
    app_config = DjangoO11yConfig("django_o11y", __import__("django_o11y"))
    resolve_side_effect = Resolver404("missing") if resolve_raises else None

    with (
        patch("django_o11y.metrics.setup.resolve", side_effect=resolve_side_effect),
        patch("django_o11y.metrics.setup.logger.warning") as mock_warning,
    ):
        app_config._configure_metrics(config)

    if warning_called:
        mock_warning.assert_called_once()
    else:
        mock_warning.assert_not_called()


@pytest.mark.parametrize(
    "file_enabled, assert_present, assert_absent",
    [
        (True, "Logging → format=console, file_dir=/tmp/django-o11y/django-app", None),
        (False, "Logging → format=console", "file_dir="),
    ],
)
def test_startup_banner_file_dir(capsys, file_enabled, assert_present, assert_absent):
    from django_o11y.apps import DjangoO11yConfig

    config = make_config(
        {
            "LOGGING": {
                "FORMAT": "console",
                "FILE_ENABLED": file_enabled,
                "FILE_PATH": "/tmp/django-o11y/django-app/django.log",
            },
            "TRACING": {"ENABLED": False},
            "METRICS": {"PROMETHEUS_ENABLED": False},
            "CELERY": {"ENABLED": False},
            "PROFILING": {"ENABLED": False},
        }
    )
    app_config = DjangoO11yConfig("django_o11y", __import__("django_o11y"))

    app_config._print_startup_banner(config)
    out = capsys.readouterr().out

    assert assert_present in out
    if assert_absent:
        assert assert_absent not in out
