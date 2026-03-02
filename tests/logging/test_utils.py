"""Tests for logging utility processors."""

import pytest


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
    from django_o11y.logging.utils import add_severity

    event_dict = {"level": level, "event": "something happened"}
    result = add_severity(None, None, event_dict)

    assert result["severity"] == expected


def test_add_severity_unknown_level_defaults_to_zero():
    from django_o11y.logging.utils import add_severity

    event_dict = {"level": "notset", "event": "something happened"}
    result = add_severity(None, None, event_dict)

    assert result["severity"] == 0


def test_add_severity_missing_level_defaults_to_zero():
    from django_o11y.logging.utils import add_severity

    event_dict = {"event": "something happened"}
    result = add_severity(None, None, event_dict)

    assert result["severity"] == 0


def test_add_severity_preserves_existing_fields():
    from django_o11y.logging.utils import add_severity

    event_dict = {"level": "info", "event": "something happened", "trace_id": "abc123"}
    result = add_severity(None, None, event_dict)

    assert result["event"] == "something happened"
    assert result["trace_id"] == "abc123"
    assert result["level"] == "info"


def test_add_severity_returns_event_dict():
    from django_o11y.logging.utils import add_severity

    event_dict = {"level": "info", "event": "x"}
    result = add_severity(None, None, event_dict)

    assert result is event_dict
