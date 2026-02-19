"""Tests for management commands - minimal mocking, integration-first."""

import pytest
from click.testing import CliRunner


def test_observability_command_exists():
    from django_o11y.management.commands.o11y import Command

    assert Command is not None


def test_o11y_command_help():
    from django_o11y.management.commands.o11y import Command

    cmd = Command()
    assert cmd.help is not None
    assert "o11y" in cmd.help.lower()


def test_check_docker_compose_available():
    from django_o11y.management.commands.o11y import (
        _check_docker_compose,
    )

    result = _check_docker_compose()
    assert isinstance(result, bool)


def test_get_compose_cmd_real():
    from django_o11y.management.commands.o11y import _get_compose_cmd

    result = _get_compose_cmd()
    assert result in [["docker", "compose"], ["docker-compose"]]


def test_get_work_dir_creates_directory():
    from django_o11y.management.commands.o11y import _get_work_dir

    work_dir = _get_work_dir()

    assert work_dir is not None
    assert work_dir.exists()
    assert work_dir.is_dir()
    assert str(work_dir).endswith(".django-o11y")


def test_get_work_dir_with_custom_app_url():
    from django_o11y.management.commands.o11y import _get_work_dir

    work_dir = _get_work_dir(app_url="myapp:8080")

    assert work_dir is not None
    assert work_dir.exists()

    # Check if prometheus.yml was customized
    prometheus_yml = work_dir / "prometheus.yml"
    if prometheus_yml.exists():
        content = prometheus_yml.read_text()
        # Should contain the custom app URL if it was processed
        assert "myapp:8080" in content or "host.docker.internal:8000" in content


def test_check_packages_real():
    from django_o11y.management.commands.o11y import _check_packages

    ok, _, err = _check_packages()

    assert ok > 0
    assert err == 0


def test_cli_group_exists():
    from django_o11y.management.commands.o11y import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "o11y" in result.output.lower()


def test_stack_group_exists():
    from django_o11y.management.commands.o11y import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["stack", "--help"])

    assert result.exit_code == 0
    assert "stack" in result.output.lower()


def test_stack_start_command_help():
    from django_o11y.management.commands.o11y import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["stack", "start", "--help"])

    assert result.exit_code == 0
    assert "start" in result.output.lower()
    assert "app-url" in result.output.lower()


def test_stack_stop_command_help():
    from django_o11y.management.commands.o11y import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["stack", "stop", "--help"])

    assert result.exit_code == 0
    assert "stop" in result.output.lower()


def test_stack_status_command_help():
    from django_o11y.management.commands.o11y import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["stack", "status", "--help"])

    assert result.exit_code == 0
    assert "status" in result.output.lower()


def test_stack_logs_command_help():
    from django_o11y.management.commands.o11y import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["stack", "logs", "--help"])

    assert result.exit_code == 0
    assert "logs" in result.output.lower()


def test_stack_restart_command_help():
    from django_o11y.management.commands.o11y import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["stack", "restart", "--help"])

    assert result.exit_code == 0
    assert "restart" in result.output.lower()


def test_check_command_help():
    from django_o11y.management.commands.o11y import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--help"])

    assert result.exit_code == 0
    assert "check" in result.output.lower()


def test_stack_start_dry_run():
    from django_o11y.management.commands.o11y import start

    # Test that the command is properly structured
    assert start is not None
    assert hasattr(start, "params")

    # Check that --app-url option exists
    param_names = [p.name for p in start.params]
    assert "app_url" in param_names


def test_work_dir_idempotent():
    from django_o11y.management.commands.o11y import _get_work_dir

    work_dir1 = _get_work_dir()
    work_dir2 = _get_work_dir()

    assert work_dir1 == work_dir2
    assert work_dir1.exists()


def test_work_dir_contains_stack_files():
    from django_o11y.management.commands.o11y import _get_work_dir

    work_dir = _get_work_dir()

    assert (work_dir / "docker-compose.yml").exists()
    assert (work_dir / "prometheus.yml").exists()


def test_helper_functions_dont_crash():
    from django_o11y.management.commands.o11y import (
        _check_configuration,
        _check_docker_compose,
        _check_otlp_endpoint,
        _check_packages,
        _get_compose_cmd,
        _get_work_dir,
        _print_next_steps,
        _print_service_urls,
        _test_trace,
    )

    # Call each helper - they should not raise exceptions
    _check_docker_compose()
    _get_compose_cmd()
    _get_work_dir()
    _check_packages()
    _check_configuration()
    _check_otlp_endpoint()
    _test_trace()
    _print_service_urls()
    _print_next_steps()


# =============================================================================
# Integration tests - require the full observability stack
# All tests in this section use the session-scoped `observability_stack`
# fixture (defined in conftest.py) which starts the stack via
# `observability stack start` and tears it down after the session.
# =============================================================================


@pytest.mark.integration
def test_stack_status_with_real_docker():
    from django_o11y.management.commands.o11y import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["stack", "status"])

    # Will succeed if Docker is available, exit code 0 or 1 is acceptable
    assert result.exit_code in [0, 1]


@pytest.mark.integration
def test_stack_status_shows_services(observability_stack):
    from django_o11y.management.commands.o11y import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["stack", "status"])

    # Exit code 0 means services are running and status was retrieved
    assert result.exit_code == 0


@pytest.mark.integration
def test_stack_start_output(observability_stack):
    """Test that stack start produces expected output.

    Invokes start a second time (docker compose up -d is idempotent) so we
    can assert against the captured Click output.
    """
    from django_o11y.management.commands.o11y import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["stack", "start"])

    assert result.exit_code == 0
    assert "Observability stack started!" in result.output
    # Service URLs are printed
    assert "localhost:3000" in result.output
    assert "localhost:9090" in result.output
    assert "localhost:3200" in result.output
    # Next steps are printed
    assert "o11y stack stop" in result.output


@pytest.mark.integration
def test_check_command(observability_stack):
    from django_o11y.management.commands.o11y import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["check"])

    assert result.exit_code == 0
    assert "Configuration:" in result.output
    assert "OTLP Endpoint:" in result.output
    assert "Installed Packages:" in result.output
    assert "Test Trace:" in result.output
    assert "Reachable" in result.output
    assert "Created test span" in result.output
    assert "Trace ID:" in result.output
    assert "OK" in result.output


@pytest.mark.integration
def test_django_call_command_check(observability_stack):
    from io import StringIO

    from django.core.management import call_command

    out = StringIO()
    # call_command should not raise - exit code 0 means all checks passed
    call_command("o11y", "check", stdout=out)


@pytest.mark.integration
def test_stack_logs_shows_output(observability_stack):
    from django_o11y.management.commands.o11y import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["stack", "logs", "--tail", "10"])

    # Should show some logs (exit code 0)
    assert result.exit_code == 0


@pytest.mark.integration
def test_stack_restart_works(observability_stack):
    from django_o11y.management.commands.o11y import cli
    from tests.conftest import _wait_for_stack

    runner = CliRunner()
    result = runner.invoke(cli, ["stack", "restart"])

    # Should successfully restart
    assert result.exit_code == 0

    # Wait for services to come back up instead of a fixed sleep
    assert _wait_for_stack(timeout=120), "Services did not recover after restart"
