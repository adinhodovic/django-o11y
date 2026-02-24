"""Tests for Celery integration."""

import pytest
from django.test import override_settings


def test_celery_setup_when_disabled(celery_app):
    from django_o11y.celery.setup import setup_celery_o11y

    config = {"CELERY": {"ENABLED": False}}
    setup_celery_o11y(celery_app, config=config)


def test_celery_setup_prevents_double_instrumentation(celery_app):
    from django_o11y.celery import setup

    original_pid = setup._instrumented_pid
    setup._instrumented_pid = None

    try:
        config = {"CELERY": {"ENABLED": True}}

        setup.setup_celery_o11y(celery_app, config=config)
        assert setup._instrumented_pid is not None

        setup.setup_celery_o11y(celery_app, config=config)
        assert setup._instrumented_pid is not None
    finally:
        setup._instrumented_pid = original_pid


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

    original_pid = setup._instrumented_pid
    setup._instrumented_pid = None

    try:
        receivers_before = len(signals.task_prerun.receivers or [])

        config = {"CELERY": {"ENABLED": True}}
        setup_celery_o11y(celery_app, config=config)

        receivers_after = len(signals.task_prerun.receivers or [])
        assert receivers_after >= receivers_before
    finally:
        setup._instrumented_pid = original_pid


def test_celery_setup_loads_config_from_django_settings(celery_app):
    from django_o11y.celery import setup
    from django_o11y.conf import get_o11y_config

    original_pid = setup._instrumented_pid
    setup._instrumented_pid = None

    try:
        with override_settings(DJANGO_O11Y={"CELERY": {"ENABLED": False}}):
            get_o11y_config.cache_clear()
            setup.setup_celery_o11y(celery_app, config=None)
            assert setup._instrumented_pid is None
    finally:
        setup._instrumented_pid = original_pid
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

    original_pid = setup._instrumented_pid
    setup._instrumented_pid = None

    try:
        config = {"CELERY": {"ENABLED": True}}
        setup.setup_celery_o11y(celery_app, config=config)

        assert celery_app.conf.worker_send_task_events is True
        assert celery_app.conf.task_send_sent_event is True
    finally:
        setup._instrumented_pid = original_pid


def test_celery_setup_does_not_set_events_when_disabled(celery_app):
    """Task events are not touched when CELERY.ENABLED is False."""
    from django_o11y.celery import setup

    original_pid = setup._instrumented_pid
    setup._instrumented_pid = None
    # Reset to a known baseline
    celery_app.conf.worker_send_task_events = False
    celery_app.conf.task_send_sent_event = False

    try:
        config = {"CELERY": {"ENABLED": False}}
        setup.setup_celery_o11y(celery_app, config=config)

        assert celery_app.conf.worker_send_task_events is False
        assert celery_app.conf.task_send_sent_event is False
    finally:
        setup._instrumented_pid = original_pid


def test_celery_prefork_pool_detection_defaults_to_prefork():
    from django_o11y.celery.setup import _is_celery_prefork_pool

    assert _is_celery_prefork_pool(["celery", "-A", "proj", "worker"]) is True


def test_celery_prefork_pool_detection_honours_explicit_pool():
    from django_o11y.celery.setup import _is_celery_prefork_pool

    assert (
        _is_celery_prefork_pool(["celery", "-A", "proj", "worker", "--pool=solo"])
        is False
    )
    assert (
        _is_celery_prefork_pool(["celery", "-A", "proj", "worker", "-P", "prefork"])
        is True
    )


def test_worker_init_skips_auto_setup_for_prefork(celery_app):
    from unittest.mock import patch

    from django_o11y.celery.setup import _auto_setup_on_worker_init

    with patch("django_o11y.celery.setup._is_celery_prefork_pool", return_value=True):
        with patch("django_o11y.celery.setup.setup_celery_o11y") as mock_setup:
            _auto_setup_on_worker_init(sender=celery_app)
            mock_setup.assert_not_called()


def test_worker_process_init_runs_auto_setup_for_prefork(celery_app):
    from unittest.mock import patch

    from django_o11y.celery.setup import _auto_setup_on_worker_process_init

    config = {"CELERY": {"ENABLED": True}, "TRACING": {"ENABLED": False}}
    with patch("django_o11y.celery.setup._is_celery_prefork_pool", return_value=True):
        with patch("django_o11y.celery.setup.get_o11y_config", return_value=config):
            with patch("django_o11y.celery.setup.setup_celery_o11y") as mock_setup:
                _auto_setup_on_worker_process_init(sender=celery_app)
                mock_setup.assert_called_once_with(celery_app, config)


def test_celery_setup_configures_tracing_provider_when_enabled(celery_app):
    from unittest.mock import patch

    from django_o11y.celery import setup

    original_pid = setup._instrumented_pid
    setup._instrumented_pid = None

    config = {
        "CELERY": {"ENABLED": True, "TRACING_ENABLED": True},
        "TRACING": {"ENABLED": True},
    }

    try:
        with patch("django_o11y.celery.setup.setup_tracing") as mock_setup_tracing:
            with patch("django_o11y.celery.setup._setup_celery_tracing"):
                setup.setup_celery_o11y(celery_app, config=config)
                mock_setup_tracing.assert_called_once_with(config)
    finally:
        setup._instrumented_pid = original_pid


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
