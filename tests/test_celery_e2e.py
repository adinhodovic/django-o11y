"""End-to-end Celery worker logging tests."""

import json
import time

import pytest
from celery import Celery
from celery.contrib.testing.worker import start_worker
from django.test import override_settings

from django_o11y.celery.setup import (
    setup_celery_o11y,
)
from django_o11y.logging.config import build_logging_dict

pytestmark = pytest.mark.integration


def test_prefork_worker_emits_json_structlog_events(tmp_path):
    """A prefork worker task log should be emitted as JSON."""
    queue_dir = tmp_path / "queue"
    processed_dir = tmp_path / "processed"
    queue_dir.mkdir()
    processed_dir.mkdir()

    log_file = tmp_path / "worker.json.log"

    logging_cfg = {
        "FORMAT": "json",
        "LEVEL": "INFO",
        "REQUEST_LEVEL": "INFO",
        "DATABASE_LEVEL": "WARNING",
        "CELERY_LEVEL": "INFO",
        "COLORIZED": False,
        "RICH_EXCEPTIONS": False,
        "OTLP_ENABLED": False,
        "OTLP_ENDPOINT": "http://localhost:4317",
        "FILE_ENABLED": True,
        "FILE_PATH": str(log_file),
        "PARSO_LEVEL": "WARNING",
        "AWS_LEVEL": "WARNING",
    }

    o11y_cfg = {
        "SERVICE_NAME": "test-service",
        "TRACING": {"ENABLED": False, "OTLP_ENDPOINT": ""},
        "LOGGING": logging_cfg,
        "CELERY": {
            "ENABLED": True,
            "TRACING_ENABLED": False,
            "LOGGING_ENABLED": True,
        },
        "PROFILING": {"ENABLED": False},
    }

    with override_settings(
        LOGGING=build_logging_dict(logging_cfg), DJANGO_O11Y=o11y_cfg
    ):
        app = Celery("e2e", broker="filesystem://", backend="cache+memory://")
        app.conf.broker_transport_options = {
            "data_folder_in": str(queue_dir),
            "data_folder_out": str(queue_dir),
            "data_folder_processed": str(processed_dir),
        }
        app.conf.worker_enable_remote_control = False

        setup_celery_o11y(app, config=o11y_cfg)

        @app.task(name="tests.e2e_json_log")
        def e2e_json_log():
            import structlog

            structlog.get_logger("tests.e2e").error("hello_from_task", foo="bar")
            return "ok"

        with start_worker(
            app,
            pool="prefork",
            concurrency=1,
            loglevel="INFO",
            perform_ping_check=False,
        ):
            e2e_json_log.delay()  # type: ignore[attr-defined]
            time.sleep(3)

        found = None
        deadline = time.time() + 10
        while time.time() < deadline:
            if log_file.exists():
                lines = log_file.read_text(encoding="utf-8").splitlines()
                for line in reversed(lines):
                    if "hello_from_task" in line:
                        found = line
                        break
            if found:
                break
            time.sleep(0.1)

        assert found is not None
        payload = json.loads(found)
        assert payload["event"] == "hello_from_task"
        assert payload["foo"] == "bar"


def test_prefork_worker_console_logs_are_json(tmp_path, capsys):
    """A prefork worker should emit JSON lines to its main logfile."""
    queue_dir = tmp_path / "queue"
    processed_dir = tmp_path / "processed"
    queue_dir.mkdir()
    processed_dir.mkdir()

    logging_cfg = {
        "FORMAT": "json",
        "LEVEL": "INFO",
        "REQUEST_LEVEL": "INFO",
        "DATABASE_LEVEL": "WARNING",
        "CELERY_LEVEL": "INFO",
        "COLORIZED": False,
        "RICH_EXCEPTIONS": False,
        "OTLP_ENABLED": False,
        "OTLP_ENDPOINT": "http://localhost:4317",
        "FILE_ENABLED": False,
        "FILE_PATH": str(tmp_path / "unused.log"),
        "PARSO_LEVEL": "WARNING",
        "AWS_LEVEL": "WARNING",
    }

    o11y_cfg = {
        "SERVICE_NAME": "test-service",
        "TRACING": {"ENABLED": False, "OTLP_ENDPOINT": ""},
        "LOGGING": logging_cfg,
        "CELERY": {
            "ENABLED": True,
            "TRACING_ENABLED": False,
            "LOGGING_ENABLED": True,
        },
        "PROFILING": {"ENABLED": False},
    }

    with override_settings(
        LOGGING=build_logging_dict(logging_cfg, extra={"root": {"level": "INFO"}}),
        DJANGO_O11Y=o11y_cfg,
    ):
        app = Celery("e2e-json", broker="filesystem://", backend="cache+memory://")
        app.conf.broker_transport_options = {
            "data_folder_in": str(queue_dir),
            "data_folder_out": str(queue_dir),
            "data_folder_processed": str(processed_dir),
        }
        app.conf.worker_enable_remote_control = False

        setup_celery_o11y(app, config=o11y_cfg)

        @app.task(name="tests.e2e_json_console")
        def e2e_json_console():
            import structlog

            structlog.get_logger("tests.e2e").error("hello_from_console", foo="bar")
            return "ok"

        with start_worker(
            app,
            pool="prefork",
            concurrency=1,
            loglevel="INFO",
            perform_ping_check=False,
        ):
            e2e_json_console.delay()  # type: ignore[attr-defined]
            time.sleep(3)

        captured = capsys.readouterr().out.splitlines()
        line = next(
            (
                candidate
                for candidate in reversed(captured)
                if "hello_from_console" in candidate
            ),
            None,
        )

        assert line is not None
        payload = json.loads(line)
        assert payload["event"] == "hello_from_console"
        assert payload["foo"] == "bar"
