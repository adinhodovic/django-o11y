"""Tests for profiling configuration."""

from unittest.mock import MagicMock, patch

import pytest


def test_profiling_disabled_by_default():
    # The hardcoded default for PROFILING.ENABLED is False
    import django.test.utils

    with django.test.utils.override_settings(DJANGO_O11Y={}):
        from django_o11y.config.setup import get_config as _get_config

        config = _get_config()
        assert config["PROFILING"]["ENABLED"] is False


def test_profiling_url_default():
    from django_o11y.config.setup import get_o11y_config

    config = get_o11y_config()

    assert config["PROFILING"]["PYROSCOPE_URL"] == "http://localhost:4040"


def test_profiling_validation():
    from django_o11y.config.utils import validate_config

    config = {
        "SERVICE_NAME": "test",
        "TRACING": {"ENABLED": True, "OTLP_ENDPOINT": "http://localhost:4317"},
        "LOGGING": {"ENABLED": True},
        "METRICS": {},
        "CELERY": {},
        "PROFILING": {
            "ENABLED": True,
            "PYROSCOPE_URL": "http://localhost:4040",
        },
    }

    errors = validate_config(config)
    assert len(errors) == 0


def test_profiling_validation_invalid_url():
    from django_o11y.config.utils import validate_config

    config = {
        "SERVICE_NAME": "test",
        "TRACING": {"ENABLED": True, "OTLP_ENDPOINT": "http://localhost:4317"},
        "LOGGING": {"ENABLED": True},
        "METRICS": {},
        "CELERY": {},
        "PROFILING": {
            "ENABLED": True,
            "PYROSCOPE_URL": "not-a-valid-url",
        },
    }

    errors = validate_config(config)
    assert len(errors) > 0
    assert any("PROFILING.PYROSCOPE_URL" in error for error in errors)


def test_profiling_can_be_enabled():
    from django_o11y.config.setup import get_o11y_config

    config = get_o11y_config()

    assert config["PROFILING"]["ENABLED"] is True
    assert config["PROFILING"]["PYROSCOPE_URL"] == "http://localhost:4040"


def test_setup_profiling_when_disabled():
    from django_o11y.profiling import setup_profiling

    config = {
        "SERVICE_NAME": "test-service",
        "PROFILING": {"ENABLED": False},
    }

    setup_profiling(config)


def test_setup_profiling_with_namespace():
    from django_o11y.profiling import setup_profiling

    mock_pyroscope = MagicMock()

    config = {
        "SERVICE_NAME": "test-service",
        "NAMESPACE": "production",
        "ENVIRONMENT": "prod",
        "PROFILING": {
            "ENABLED": True,
            "PYROSCOPE_URL": "http://localhost:4040",
        },
    }

    with patch.dict("sys.modules", {"pyroscope": mock_pyroscope}):
        setup_profiling(config)

        mock_pyroscope.configure.assert_called_once()
        call_kwargs = mock_pyroscope.configure.call_args[1]
        assert "service_namespace" in call_kwargs["tags"]
        assert call_kwargs["tags"]["service_namespace"] == "production"


def test_setup_profiling_without_namespace():
    from django_o11y.profiling import setup_profiling

    mock_pyroscope = MagicMock()

    config = {
        "SERVICE_NAME": "test-service",
        "ENVIRONMENT": "dev",
        "PROFILING": {
            "ENABLED": True,
            "PYROSCOPE_URL": "http://localhost:4040",
        },
    }

    with patch.dict("sys.modules", {"pyroscope": mock_pyroscope}):
        setup_profiling(config)

        mock_pyroscope.configure.assert_called_once()
        call_kwargs = mock_pyroscope.configure.call_args[1]
        assert "service_namespace" not in call_kwargs["tags"]


def test_setup_profiling_with_custom_tags():
    from django_o11y.profiling import setup_profiling

    mock_pyroscope = MagicMock()

    config = {
        "SERVICE_NAME": "test-service",
        "ENVIRONMENT": "staging",
        "RESOURCE_ATTRIBUTES": {
            "region": "us-west-2",
            "team": "backend",
        },
        "PROFILING": {
            "ENABLED": True,
            "PYROSCOPE_URL": "http://localhost:4040",
        },
    }

    with patch.dict("sys.modules", {"pyroscope": mock_pyroscope}):
        setup_profiling(config)

        mock_pyroscope.configure.assert_called_once()
        call_kwargs = mock_pyroscope.configure.call_args[1]
        assert call_kwargs["tags"]["region"] == "us-west-2"
        assert call_kwargs["tags"]["team"] == "backend"


def test_setup_profiling_handles_import_error():
    import importlib

    from django_o11y.profiling import setup_profiling

    config = {
        "SERVICE_NAME": "test-service",
        "PROFILING": {
            "ENABLED": True,
            "PYROSCOPE_URL": "http://localhost:4040",
        },
    }

    def mock_import(name, *args, **kwargs):
        if name == "pyroscope":
            raise ImportError("pyroscope not installed")
        return importlib.__import__(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        setup_profiling(config)


def test_setup_profiling_raises_on_configure_error():
    from django_o11y.profiling import setup_profiling

    mock_pyroscope = MagicMock()
    mock_pyroscope.configure.side_effect = RuntimeError("Connection failed")

    config = {
        "SERVICE_NAME": "test-service",
        "PROFILING": {
            "ENABLED": True,
            "PYROSCOPE_URL": "http://localhost:4040",
        },
    }

    with patch.dict("sys.modules", {"pyroscope": mock_pyroscope}):
        with pytest.raises(RuntimeError, match="Connection failed"):
            setup_profiling(config)


def test_setup_profiling_skips_pyroscope_configure_in_celery_prefork_boot():
    """setup_profiling must skip pyroscope in celery prefork boot process."""
    from django_o11y.profiling import setup_profiling

    mock_pyroscope = MagicMock()

    config = {
        "SERVICE_NAME": "test-service",
        "PROFILING": {
            "ENABLED": True,
            "PYROSCOPE_URL": "http://localhost:4040",
        },
    }

    with patch("sys.argv", ["celery", "-A", "proj", "worker"]):
        with patch.dict("sys.modules", {"pyroscope": mock_pyroscope}):
            setup_profiling(config)

            mock_pyroscope.configure.assert_not_called()


def test_setup_profiling_allows_prefork_child_process():
    """setup_profiling runs in celery prefork child workers."""
    from django_o11y.profiling import setup_profiling

    mock_pyroscope = MagicMock()

    config = {
        "SERVICE_NAME": "test-service",
        "PROFILING": {
            "ENABLED": True,
            "PYROSCOPE_URL": "http://localhost:4040",
        },
    }

    with patch("sys.argv", ["celery", "-A", "proj", "worker"]):
        with patch(
            "django_o11y.profiling.setup.is_celery_fork_pool_worker",
            return_value=True,
        ):
            with patch.dict("sys.modules", {"pyroscope": mock_pyroscope}):
                setup_profiling(config)

                mock_pyroscope.configure.assert_called_once()
