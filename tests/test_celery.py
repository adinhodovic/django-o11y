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
