"""Tests for Celery integration."""

from django.test import override_settings


def test_celery_setup_when_disabled(celery_app):
    from django_o11y.tracing.setup import setup_celery_o11y

    config = {"CELERY": {"ENABLED": False}}
    setup_celery_o11y(celery_app, config=config)


def test_celery_setup_prevents_double_instrumentation(celery_app):
    from django_o11y.tracing import setup

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

    from django_o11y.tracing.setup import _setup_celery_tracing

    def mock_import(name, *args, **kwargs):
        if name == "opentelemetry.instrumentation.celery":
            raise ImportError("No module named 'opentelemetry.instrumentation.celery'")
        return importlib.__import__(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        with patch("django_o11y.tracing.setup.logger.warning") as mock_warning:
            _setup_celery_tracing()
            mock_warning.assert_called_once()


def test_celery_setup_connects_signals(celery_app):
    from celery import signals

    from django_o11y.tracing import setup
    from django_o11y.tracing.setup import setup_celery_o11y

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
    from django_o11y.config.setup import get_o11y_config
    from django_o11y.tracing import setup

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
    from django_o11y.config.setup import get_o11y_config
    from django_o11y.tracing.signals import _auto_setup_on_worker_init

    with override_settings(DJANGO_O11Y={"CELERY": {"ENABLED": False}}):
        get_o11y_config.cache_clear()
        _auto_setup_on_worker_init(sender=celery_app)
        get_o11y_config.cache_clear()


def test_configure_celery_metrics_events_sets_flags(celery_app):
    """_configure_celery_metrics_events sets worker and task event flags."""
    from unittest.mock import patch

    from django_o11y.tracing.setup import _configure_celery_metrics_events

    config = {
        "CELERY": {"ENABLED": True, "METRICS_ENABLED": True},
        "METRICS": {"PROMETHEUS_ENABLED": True},
    }

    with patch("celery.current_app", celery_app):
        _configure_celery_metrics_events(config)

    assert celery_app.conf.worker_send_task_events is True
    assert celery_app.conf.task_send_sent_event is True


def test_configure_celery_metrics_events_skips_when_metrics_disabled(celery_app):
    """Task events are not set when Prometheus metrics are disabled."""
    from unittest.mock import patch

    from django_o11y.tracing.setup import _configure_celery_metrics_events

    celery_app.conf.worker_send_task_events = False
    celery_app.conf.task_send_sent_event = False

    config = {
        "CELERY": {"ENABLED": True, "METRICS_ENABLED": True},
        "METRICS": {"PROMETHEUS_ENABLED": False},
    }

    with patch("celery.current_app", celery_app):
        _configure_celery_metrics_events(config)

    assert celery_app.conf.worker_send_task_events is False
    assert celery_app.conf.task_send_sent_event is False


def test_celery_prefork_pool_detection_defaults_to_prefork():
    from django_o11y.tracing.utils import is_celery_prefork_pool

    assert is_celery_prefork_pool(["celery", "-A", "proj", "worker"]) is True


def test_celery_prefork_pool_detection_honours_explicit_pool():
    from django_o11y.tracing.utils import is_celery_prefork_pool

    assert (
        is_celery_prefork_pool(["celery", "-A", "proj", "worker", "--pool=solo"])
        is False
    )
    assert (
        is_celery_prefork_pool(["celery", "-A", "proj", "worker", "-P", "prefork"])
        is True
    )


def test_celery_prefork_pool_detection_false_for_non_worker():
    """is_celery_prefork_pool must return False for non-worker commands."""
    from django_o11y.tracing.utils import is_celery_prefork_pool

    assert is_celery_prefork_pool(["celery", "-A", "proj", "beat"]) is False
    assert is_celery_prefork_pool(["gunicorn", "myapp.wsgi"]) is False


def test_worker_init_skips_auto_setup_for_prefork(celery_app):
    from unittest.mock import patch

    from django_o11y.tracing.signals import _auto_setup_on_worker_init

    with patch("django_o11y.tracing.signals.is_celery_prefork_pool", return_value=True):
        with patch("django_o11y.tracing.signals._auto_setup_worker") as mock_setup:
            _auto_setup_on_worker_init(sender=celery_app)
            mock_setup.assert_not_called()


def test_worker_process_init_runs_auto_setup_for_prefork(celery_app):
    """worker_process_init fires with sender=None in real Celery prefork workers.

    The handler must fall back to ``celery.current_app`` and pass a real app
    instance to setup_celery_o11y instead of None.
    """
    from unittest.mock import patch

    import celery as _celery

    from django_o11y.tracing.signals import _auto_setup_on_worker_process_init

    config = {"CELERY": {"ENABLED": True}, "TRACING": {"ENABLED": False}}
    with patch("django_o11y.tracing.signals.is_celery_prefork_pool", return_value=True):
        with patch("django_o11y.tracing.signals.get_o11y_config", return_value=config):
            with patch(
                "django_o11y.tracing.signals._resolve_worker_app",
                return_value=_celery.current_app,
            ):
                with patch("django_o11y.tracing.setup.setup_celery_o11y") as mock_setup:
                    # sender=None mirrors what celery/concurrency/prefork.py
                    # actually sends.
                    _auto_setup_on_worker_process_init(sender=None)
                    mock_setup.assert_called_once_with(_celery.current_app, config)


def test_worker_process_init_sets_up_profiling_for_prefork_child(celery_app):
    """Prefork child worker should initialize profiling post-fork."""
    from unittest.mock import patch

    from django_o11y.profiling.signals import (
        _auto_setup_profiling_on_worker_process_init,
    )

    config = {
        "CELERY": {"ENABLED": True},
        "TRACING": {"ENABLED": False},
        "PROFILING": {"ENABLED": True},
    }
    with patch(
        "django_o11y.profiling.signals.is_celery_prefork_pool", return_value=True
    ):
        with patch(
            "django_o11y.profiling.signals.get_o11y_config", return_value=config
        ):
            with patch(
                "django_o11y.profiling.signals.is_celery_fork_pool_worker",
                return_value=True,
            ):
                with patch(
                    "django_o11y.profiling.setup.setup_profiling"
                ) as mock_profile:
                    _auto_setup_profiling_on_worker_process_init(sender=None)
                    mock_profile.assert_called_once_with(config)


def test_worker_process_shutdown_flushes_traces_when_enabled():
    from unittest.mock import patch

    from django_o11y.tracing.signals import _auto_flush_on_worker_process_shutdown

    config = {
        "CELERY": {"ENABLED": True},
        "TRACING": {"ENABLED": True},
    }

    with patch("django_o11y.tracing.signals.get_o11y_config", return_value=config):
        with patch("django_o11y.tracing.signals._maybe_force_flush") as mock_flush:
            _auto_flush_on_worker_process_shutdown(sender=None)
            mock_flush.assert_called_once_with(config, reason="worker_process_shutdown")


def test_celery_setup_configures_tracing_provider_when_enabled(celery_app):
    from unittest.mock import patch

    from django_o11y.tracing import setup

    original_pid = setup._instrumented_pid
    setup._instrumented_pid = None

    config = {
        "CELERY": {"ENABLED": True, "TRACING_ENABLED": True},
        "TRACING": {"ENABLED": True},
    }

    try:
        with patch("django_o11y.tracing.setup.setup_celery_logging") as mock_logging:
            with patch(
                "django_o11y.tracing.setup.setup_instrumentation"
            ) as mock_setup_instrumentation:
                with patch(
                    "django_o11y.tracing.setup.setup_tracing"
                ) as mock_setup_tracing:
                    with patch("django_o11y.tracing.setup._setup_celery_tracing"):
                        setup.setup_celery_o11y(celery_app, config=config)
                        mock_logging.assert_called_once_with(celery_app)
                        mock_setup_instrumentation.assert_called_once_with(config)
                        mock_setup_tracing.assert_called_once_with(config)
    finally:
        setup._instrumented_pid = original_pid


def test_celery_logging_handler_connected_to_setup_logging_signal():
    """setup_logging has django-o11y logging receiver connected."""
    import importlib

    from celery.signals import setup_logging

    importlib.import_module("django_o11y.logging.signals")

    # setup.py registers handler at import time via decorator.
    assert len(setup_logging.receivers or []) >= 1


def test_setup_logging_signal_applies_django_logging_config(celery_app):
    """setup_logging receiver applies Django LOGGING config."""
    import logging.config as lc
    from unittest.mock import patch

    fake_logging = {"version": 1, "disable_existing_loggers": False}

    import django_o11y.logging.signals as _logging_setup  # noqa: F401

    with override_settings(LOGGING=fake_logging):
        with patch.object(lc, "dictConfig") as mock_dictconfig:
            # Handler should run only when Celery emits setup_logging.
            mock_dictconfig.assert_not_called()

            # Simulate Celery firing the setup_logging signal on worker start
            from celery.signals import setup_logging

            setup_logging.send(sender=None)
            # The handler may fire multiple times if earlier tests also
            # registered receivers (weak=False keeps them alive).  Assert
            # it was called at least once with the right config dict.
            mock_dictconfig.assert_called_with(fake_logging)
            assert mock_dictconfig.call_count >= 1


def test_celery_setup_disables_worker_root_logger_hijack(celery_app):
    """setup_celery_o11y disables Celery root logger hijacking."""
    from django_o11y.tracing import setup

    original_pid = setup._instrumented_pid
    setup._instrumented_pid = None

    try:
        celery_app.conf.worker_hijack_root_logger = True
        config = {"CELERY": {"ENABLED": True}}
        setup.setup_celery_o11y(celery_app, config=config)

        assert celery_app.conf.worker_hijack_root_logger is False
    finally:
        setup._instrumented_pid = original_pid


def test_setup_celery_adds_django_structlog_worker_step(celery_app):
    """setup_celery_o11y registers django-structlog worker init step."""
    from types import SimpleNamespace
    from unittest.mock import Mock, patch

    from django_o11y.tracing import setup

    original_pid = setup._instrumented_pid
    setup._instrumented_pid = None

    try:
        fake_worker_steps = Mock()
        fake_app = Mock()
        fake_app.conf = SimpleNamespace()
        fake_app.steps = {"worker": fake_worker_steps}
        config = {"CELERY": {"ENABLED": True}}
        with patch("django_o11y.logging.celery.logger.info") as mock_info:
            setup.setup_celery_o11y(fake_app, config=config)

        fake_worker_steps.add.assert_called_once()
        mock_info.assert_any_call(
            "celery_worker_step_registered",
            step="DjangoStructLogInitStep",
            pid=setup.os.getpid(),
        )
    finally:
        setup._instrumented_pid = original_pid


def test_connect_worker_receivers_once_per_pid():
    """CeleryReceiver worker signals are connected once per process."""
    from unittest.mock import patch

    from django_o11y.logging import celery as celery_logging

    original_receivers = dict(celery_logging._worker_receivers_by_pid)
    celery_logging._worker_receivers_by_pid.clear()

    try:
        with patch("django_structlog.celery.receivers.CeleryReceiver") as receiver_cls:
            receiver = receiver_cls.return_value

            celery_logging._connect_worker_receivers_once_per_pid()
            celery_logging._connect_worker_receivers_once_per_pid()

            receiver_cls.assert_called_once()
            receiver.connect_worker_signals.assert_called_once()
            assert (
                celery_logging._worker_receivers_by_pid[celery_logging.os.getpid()]
                is receiver
            )
    finally:
        celery_logging._worker_receivers_by_pid.clear()
        celery_logging._worker_receivers_by_pid.update(original_receivers)
