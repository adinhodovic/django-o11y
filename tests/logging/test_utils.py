"""Tests for logging utility processors."""

import pytest

from django_o11y.logging.utils import add_severity


@pytest.mark.parametrize(
    "level, expected",
    [
        ("debug", 100),
        ("info", 200),
        ("warning", 400),
        ("error", 500),
        ("critical", 600),
    ],
)
def test_add_severity_maps_known_levels(level, expected):
    result = add_severity(None, None, {"level": level, "event": "something happened"})
    assert result["severity"] == expected


@pytest.mark.parametrize(
    "event_dict",
    [
        {"level": "notset", "event": "something happened"},
        {"event": "something happened"},
    ],
    ids=["unknown_level", "missing_level"],
)
def test_add_severity_defaults_to_zero(event_dict):
    assert add_severity(None, None, event_dict)["severity"] == 0


def test_add_severity_preserves_existing_fields():
    event_dict = {"level": "info", "event": "something happened", "trace_id": "abc123"}
    result = add_severity(None, None, event_dict)

    assert result["event"] == "something happened"
    assert result["trace_id"] == "abc123"
    assert result["level"] == "info"


def test_add_severity_returns_event_dict():
    event_dict = {"level": "info", "event": "x"}
    assert add_severity(None, None, event_dict) is event_dict
