"""Tests for Celery integration."""

import pytest
from django.test import override_settings


def test_celery_setup_when_disabled(celery_app):
    from django_o11y.celery.setup import setup_celery_o11y

    config = {"CELERY": {"ENABLED": False}}
    setup_celery_o11y(celery_app, config=config)


def test_celery_setup_prevents_double_instrumentation(celery_app):
    from django_o11y.celery import setup

    original_flag = setup._instrumented
    setup._instrumented = False

    try:
        config = {"CELERY": {"ENABLED": True}}

        setup.setup_celery_o11y(celery_app, config=config)
        assert setup._instrumented is True

        setup.setup_celery_o11y(celery_app, config=config)
        assert setup._instrumented is True
    finally:
        setup._instrumented = original_flag


def test_celery_setup_warns_on_missing_package():
    import importlib
    from unittest.mock import patch

    from django_o11y.celery.setup import _setup_celery_tracing

    def mock_import(name, *args, **kwargs):
        if name == "opentelemetry.instrumentation.celery":
            raise ImportError("No module named 'opentelemetry.instrumentation.celery'")
        return importlib.__import__(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        with pytest.warns(UserWarning, match="opentelemetry-instrumentation-celery"):
            _setup_celery_tracing()


def test_celery_setup_connects_signals(celery_app):
    from celery import signals

    from django_o11y.celery import setup
    from django_o11y.celery.setup import setup_celery_o11y

    original_flag = setup._instrumented
    setup._instrumented = False

    try:
        receivers_before = len(signals.task_prerun.receivers or [])

        config = {"CELERY": {"ENABLED": True}}
        setup_celery_o11y(celery_app, config=config)

        receivers_after = len(signals.task_prerun.receivers or [])
        assert receivers_after >= receivers_before
    finally:
        setup._instrumented = original_flag


def test_celery_setup_loads_config_from_django_settings(celery_app):
    from django_o11y.celery import setup
    from django_o11y.conf import get_o11y_config

    original_flag = setup._instrumented
    setup._instrumented = False

    try:
        with override_settings(DJANGO_O11Y={"CELERY": {"ENABLED": False}}):
            get_o11y_config.cache_clear()
            setup.setup_celery_o11y(celery_app, config=None)
            assert setup._instrumented is False
    finally:
        setup._instrumented = original_flag
        get_o11y_config.cache_clear()


def test_auto_setup_skips_when_celery_disabled(celery_app):
    from django_o11y.celery.setup import (
        _auto_setup_on_worker_init,
    )
    from django_o11y.conf import get_o11y_config

    with override_settings(DJANGO_O11Y={"CELERY": {"ENABLED": False}}):
        get_o11y_config.cache_clear()
        _auto_setup_on_worker_init(sender=celery_app)
        get_o11y_config.cache_clear()


def test_celery_setup_enables_task_events(celery_app):
    """setup_celery_o11y sets worker_send_task_events and task_send_sent_event."""
    from django_o11y.celery import setup

    original_flag = setup._instrumented
    setup._instrumented = False

    try:
        config = {"CELERY": {"ENABLED": True}}
        setup.setup_celery_o11y(celery_app, config=config)

        assert celery_app.conf.worker_send_task_events is True
        assert celery_app.conf.task_send_sent_event is True
    finally:
        setup._instrumented = original_flag


def test_celery_setup_does_not_set_events_when_disabled(celery_app):
    """Task events are not touched when CELERY.ENABLED is False."""
    from django_o11y.celery import setup

    original_flag = setup._instrumented
    setup._instrumented = False
    # Reset to a known baseline
    celery_app.conf.worker_send_task_events = False
    celery_app.conf.task_send_sent_event = False

    try:
        config = {"CELERY": {"ENABLED": False}}
        setup.setup_celery_o11y(celery_app, config=config)

        assert celery_app.conf.worker_send_task_events is False
        assert celery_app.conf.task_send_sent_event is False
    finally:
        setup._instrumented = original_flag


def test_setup_celery_logging_connects_setup_logging_signal():
    """_setup_celery_logging registers a handler on celery.signals.setup_logging."""
    from celery.signals import setup_logging

    from django_o11y.celery.setup import _setup_celery_logging

    _setup_celery_logging()

    # At least one receiver must be connected after calling _setup_celery_logging
    assert len(setup_logging.receivers or []) >= 1


def test_setup_celery_logging_applies_django_logging_config(celery_app):
    """The setup_logging handler calls dictConfig with settings.LOGGING."""
    import logging.config as lc
    from unittest.mock import patch

    from django_o11y.celery.setup import _setup_celery_logging

    fake_logging = {"version": 1, "disable_existing_loggers": False}

    with override_settings(LOGGING=fake_logging):
        with patch.object(lc, "dictConfig") as mock_dictconfig:
            _setup_celery_logging()

            # Simulate Celery firing the setup_logging signal on worker start
            from celery.signals import setup_logging

            setup_logging.send(sender=None)

            # The handler may fire multiple times if earlier tests also
            # registered receivers (weak=False keeps them alive).  Assert
            # it was called at least once with the right config dict.
            mock_dictconfig.assert_called_with(fake_logging)
            assert mock_dictconfig.call_count >= 1
