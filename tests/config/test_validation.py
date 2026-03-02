"""Tests for configuration validation."""

import pytest


def test_valid_config():
    from django_o11y.config.utils import validate_config

    config = {
        "TRACING": {"SAMPLE_RATE": 0.5},
        "LOGGING": {"FORMAT": "json", "LEVEL": "INFO"},
        "METRICS": {"PROMETHEUS_ENABLED": True},
    }

    errors = validate_config(config)
    assert len(errors) == 0


@pytest.mark.parametrize(
    "config, expected_fragments",
    [
        ({"TRACING": {"SAMPLE_RATE": 1.5}}, ["SAMPLE_RATE", "0.0 and 1.0"]),
        ({"TRACING": {"SAMPLE_RATE": -0.1}}, ["SAMPLE_RATE"]),
        ({"TRACING": {"SAMPLE_RATE": "high"}}, ["must be a number"]),
        ({"LOGGING": {"FORMAT": "xml"}}, ["FORMAT", "console", "json"]),
        ({"LOGGING": {"LEVEL": "TRACE"}}, ["LEVEL"]),
        (
            {"TRACING": {"OTLP_ENDPOINT": "grpc://localhost:4317"}},
            ["OTLP_ENDPOINT", "http://"],
        ),
        (
            {
                "LOGGING": {
                    "OTLP_ENABLED": True,
                    "OTLP_ENDPOINT": "grpc://localhost:4317",
                }
            },
            ["LOGGING.OTLP_ENDPOINT"],
        ),
        (
            {"PROFILING": {"PYROSCOPE_URL": "grpc://pyroscope:4040"}},
            ["PROFILING.PYROSCOPE_URL"],
        ),
    ],
)
def test_invalid_config_produces_error(config, expected_fragments):
    from django_o11y.config.utils import validate_config

    errors = validate_config(config)
    assert len(errors) >= 1
    combined = " ".join(errors)
    for fragment in expected_fragments:
        assert fragment in combined


def test_multiple_validation_errors():
    from django_o11y.config.utils import validate_config

    config = {
        "TRACING": {"SAMPLE_RATE": 2.0},
        "LOGGING": {"FORMAT": "yaml", "LEVEL": "INVALID"},
    }

    errors = validate_config(config)
    assert len(errors) == 3


def test_empty_config():
    from django_o11y.config.utils import validate_config

    config = {}

    errors = validate_config(config)
    assert len(errors) == 0


def test_endpoint_non_string():
    from django_o11y.config.utils import _validate_endpoint

    errors = _validate_endpoint(12345, "TRACING.OTLP_ENDPOINT")
    assert len(errors) == 1
    assert "must be a string" in errors[0]
