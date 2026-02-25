"""Tests for fork-safety (pre-fork server reinitialisation)."""

from unittest.mock import MagicMock, patch


def test_register_post_fork_handler_idempotent():
    """register_post_fork_handler only calls os.register_at_fork once."""
    import django_o11y.tracing.fork as fork_module

    original = fork_module._fork_handler_registered
    fork_module._fork_handler_registered = False

    try:
        with patch("os.register_at_fork") as mock_register:
            fork_module.register_post_fork_handler()
            fork_module.register_post_fork_handler()
            fork_module.register_post_fork_handler()

        assert mock_register.call_count == 1
        assert fork_module._fork_handler_registered is True
    finally:
        fork_module._fork_handler_registered = original


def test_register_post_fork_handler_passes_correct_hook():
    """register_post_fork_handler wires _reinit_after_fork as after_in_child."""
    import django_o11y.tracing.fork as fork_module

    original = fork_module._fork_handler_registered
    fork_module._fork_handler_registered = False

    try:
        with patch("os.register_at_fork") as mock_register:
            fork_module.register_post_fork_handler()

        mock_register.assert_called_once_with(
            after_in_child=fork_module._reinit_after_fork
        )
    finally:
        fork_module._fork_handler_registered = original


def test_reinit_after_fork_shuts_down_and_reinitialises(mock_config):
    """_reinit_after_fork shuts down the old provider and calls setup_tracing."""
    mock_config["TRACING"]["ENABLED"] = True

    mock_provider = MagicMock()

    with (
        patch("django_o11y.tracing.fork.get_o11y_config", return_value=mock_config),
        patch("django_o11y.tracing.fork.trace") as mock_trace,
        patch("django_o11y.tracing.setup.setup_tracing") as mock_setup,
    ):
        mock_trace.get_tracer_provider.return_value = mock_provider

        from django_o11y.tracing.fork import _reinit_after_fork

        _reinit_after_fork()

    mock_provider.shutdown.assert_called_once()
    mock_setup.assert_called_once_with(mock_config)


def test_reinit_after_fork_skips_when_tracing_disabled(mock_config):
    """_reinit_after_fork does nothing when TRACING.ENABLED is False."""
    mock_config["TRACING"]["ENABLED"] = False

    with (
        patch("django_o11y.tracing.fork.get_o11y_config", return_value=mock_config),
        patch("django_o11y.tracing.setup.setup_tracing") as mock_setup,
    ):
        from django_o11y.tracing.fork import _reinit_after_fork

        _reinit_after_fork()

    mock_setup.assert_not_called()


def test_reinit_after_fork_handles_shutdown_exception(mock_config):
    """_reinit_after_fork continues past a shutdown error and still reinitialises."""
    mock_config["TRACING"]["ENABLED"] = True

    mock_provider = MagicMock()
    mock_provider.shutdown.side_effect = RuntimeError("broken channel")

    with (
        patch("django_o11y.tracing.fork.get_o11y_config", return_value=mock_config),
        patch("django_o11y.tracing.fork.trace") as mock_trace,
        patch("django_o11y.tracing.setup.setup_tracing") as mock_setup,
    ):
        mock_trace.get_tracer_provider.return_value = mock_provider

        from django_o11y.tracing.fork import _reinit_after_fork

        # Must not raise
        _reinit_after_fork()

    # setup_tracing is still called even if shutdown raised
    mock_setup.assert_called_once_with(mock_config)


def test_reinit_after_fork_handles_top_level_exception():
    """_reinit_after_fork swallows all exceptions so the worker boots cleanly."""
    with (
        patch(
            "django_o11y.tracing.fork.get_o11y_config",
            side_effect=RuntimeError("config boom"),
        ),
    ):
        from django_o11y.tracing.fork import _reinit_after_fork

        # Must not raise
        _reinit_after_fork()


def test_setup_tracing_uses_worker_pid_after_fork():
    """setup_tracing computes SERVICE_INSTANCE_ID from os.getpid() at call time.

    When no explicit SERVICE_INSTANCE_ID is configured, the resource should
    reflect the current process's pid — not a cached master pid.
    """
    import os

    from django_o11y.tracing.setup import setup_tracing

    config = {
        "SERVICE_NAME": "test-service",
        "SERVICE_VERSION": "1.0",
        "SERVICE_INSTANCE_ID": None,  # no explicit override → use hostname:pid
        "ENVIRONMENT": "test",
        "TRACING": {"OTLP_ENDPOINT": None, "CONSOLE_EXPORTER": False},
        "PROFILING": {"ENABLED": False},
        "RESOURCE_ATTRIBUTES": {},
    }

    with (
        patch("django_o11y.tracing.utils.trace.set_tracer_provider"),
    ):
        provider = setup_tracing(config)

    instance_id = provider.resource.attributes.get("service.instance.id")
    assert instance_id is not None
    assert str(os.getpid()) in instance_id
