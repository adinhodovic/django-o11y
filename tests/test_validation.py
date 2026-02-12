"""Tests for configuration validation."""

import pytest


def test_valid_config():
    from django_observability.validation import validate_config

    config = {
        "TRACING": {"SAMPLE_RATE": 0.5},
        "LOGGING": {"FORMAT": "json", "LEVEL": "INFO"},
        "METRICS": {"EXPORT_INTERVAL": 15},
    }

    errors = validate_config(config)
    assert len(errors) == 0


def test_invalid_sample_rate_too_high():
    from django_observability.validation import validate_config

    config = {
        "TRACING": {"SAMPLE_RATE": 1.5},
    }

    errors = validate_config(config)
    assert len(errors) == 1
    assert "SAMPLE_RATE" in errors[0]
    assert "0.0 and 1.0" in errors[0]


def test_invalid_sample_rate_negative():
    from django_observability.validation import validate_config

    config = {
        "TRACING": {"SAMPLE_RATE": -0.1},
    }

    errors = validate_config(config)
    assert len(errors) == 1
    assert "SAMPLE_RATE" in errors[0]


def test_invalid_log_format():
    from django_observability.validation import validate_config

    config = {
        "LOGGING": {"FORMAT": "xml"},
    }

    errors = validate_config(config)
    assert len(errors) == 1
    assert "FORMAT" in errors[0]
    assert "console" in errors[0]
    assert "json" in errors[0]


def test_invalid_log_level():
    from django_observability.validation import validate_config

    config = {
        "LOGGING": {"LEVEL": "TRACE"},
    }

    errors = validate_config(config)
    assert len(errors) == 1
    assert "LEVEL" in errors[0]


def test_invalid_otlp_endpoint():
    from django_observability.validation import validate_config

    config = {
        "TRACING": {"OTLP_ENDPOINT": "grpc://localhost:4317"},
    }

    errors = validate_config(config)
    assert len(errors) == 1
    assert "OTLP_ENDPOINT" in errors[0]
    assert "http://" in errors[0]


def test_invalid_export_interval():
    from django_observability.validation import validate_config

    config = {
        "METRICS": {"EXPORT_INTERVAL": 0},
    }

    errors = validate_config(config)
    assert len(errors) == 1
    assert "EXPORT_INTERVAL" in errors[0]


def test_multiple_validation_errors():
    from django_observability.validation import validate_config

    config = {
        "TRACING": {"SAMPLE_RATE": 2.0},
        "LOGGING": {"FORMAT": "yaml", "LEVEL": "INVALID"},
        "METRICS": {"EXPORT_INTERVAL": -1},
    }

    errors = validate_config(config)
    assert len(errors) == 4


def test_empty_config():
    from django_observability.validation import validate_config

    config = {}

    errors = validate_config(config)
    assert len(errors) == 0


def test_invalid_sample_rate_not_a_number():
    from django_observability.validation import validate_config

    errors = validate_config({"TRACING": {"SAMPLE_RATE": "high"}})
    assert len(errors) == 1
    assert "must be a number" in errors[0]


def test_logging_otlp_endpoint_validated_when_enabled():
    from django_observability.validation import validate_config

    errors = validate_config(
        {
            "LOGGING": {
                "OTLP_ENABLED": True,
                "OTLP_ENDPOINT": "grpc://localhost:4317",
            }
        }
    )
    assert any("LOGGING.OTLP_ENDPOINT" in e for e in errors)


def test_metrics_export_interval_not_int():
    from django_observability.validation import validate_config

    errors = validate_config({"METRICS": {"EXPORT_INTERVAL": 1.5}})
    assert len(errors) == 1
    assert "integer" in errors[0]


def test_metrics_otlp_endpoint_validated_when_enabled():
    from django_observability.validation import validate_config

    errors = validate_config(
        {
            "METRICS": {
                "OTLP_ENABLED": True,
                "OTLP_ENDPOINT": "grpc://localhost:4317",
            }
        }
    )
    assert any("METRICS.OTLP_ENDPOINT" in e for e in errors)


def test_profiling_pyroscope_url_validated():
    from django_observability.validation import validate_config

    errors = validate_config({"PROFILING": {"PYROSCOPE_URL": "grpc://pyroscope:4040"}})
    assert any("PROFILING.PYROSCOPE_URL" in e for e in errors)


def test_endpoint_non_string():
    from django_observability.validation import _validate_endpoint

    errors = _validate_endpoint(12345, "TRACING.OTLP_ENDPOINT")
    assert len(errors) == 1
    assert "must be a string" in errors[0]
