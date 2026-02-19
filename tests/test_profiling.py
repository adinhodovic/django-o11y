"""Tests for profiling configuration."""

from unittest.mock import patch, MagicMock


def test_profiling_disabled_by_default():
    import os

    old_env = os.environ.get("DJANGO_OBSERVABILITY_PROFILING_ENABLED")

    try:
        if "DJANGO_OBSERVABILITY_PROFILING_ENABLED" in os.environ:
            del os.environ["DJANGO_OBSERVABILITY_PROFILING_ENABLED"]

        from django_observability.conf import _get_bool_env

        default_value = _get_bool_env("DJANGO_OBSERVABILITY_PROFILING_ENABLED", False)
        assert default_value is False
    finally:
        if old_env is not None:
            os.environ["DJANGO_OBSERVABILITY_PROFILING_ENABLED"] = old_env


def test_profiling_url_default():
    from django_observability.conf import get_observability_config

    config = get_observability_config()

    assert config["PROFILING"]["PYROSCOPE_URL"] == "http://localhost:4040"


def test_profiling_validation():
    from django_observability.validation import validate_config

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
    from django_observability.validation import validate_config

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
    from django_observability.conf import get_observability_config

    config = get_observability_config()

    assert config["PROFILING"]["ENABLED"] is True
    assert config["PROFILING"]["PYROSCOPE_URL"] == "http://localhost:4040"


def test_setup_profiling_when_disabled():
    from django_observability.profiling import setup_profiling

    config = {
        "SERVICE_NAME": "test-service",
        "PROFILING": {"ENABLED": False},
    }

    setup_profiling(config)


def test_setup_profiling_with_namespace():
    from django_observability.profiling import setup_profiling

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
    from django_observability.profiling import setup_profiling

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
    from django_observability.profiling import setup_profiling

    mock_pyroscope = MagicMock()

    config = {
        "SERVICE_NAME": "test-service",
        "ENVIRONMENT": "staging",
        "PROFILING": {
            "ENABLED": True,
            "PYROSCOPE_URL": "http://localhost:4040",
            "TAGS": {
                "region": "us-west-2",
                "team": "backend",
            },
        },
    }

    with patch.dict("sys.modules", {"pyroscope": mock_pyroscope}):
        setup_profiling(config)

        mock_pyroscope.configure.assert_called_once()
        call_kwargs = mock_pyroscope.configure.call_args[1]
        assert call_kwargs["tags"]["region"] == "us-west-2"
        assert call_kwargs["tags"]["team"] == "backend"


def test_setup_profiling_handles_import_error():
    from django_observability.profiling import setup_profiling

    config = {
        "SERVICE_NAME": "test-service",
        "PROFILING": {
            "ENABLED": True,
            "PYROSCOPE_URL": "http://localhost:4040",
        },
    }

    with patch(
        "builtins.__import__", side_effect=ImportError("pyroscope not installed")
    ):
        setup_profiling(config)


def test_setup_profiling_handles_generic_exception():
    from django_observability.profiling import setup_profiling

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
        setup_profiling(config)
