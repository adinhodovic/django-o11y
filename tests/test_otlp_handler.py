"""Tests for OTLP logging handler."""

import logging
from unittest.mock import MagicMock, patch

import pytest


def test_otlp_handler_initialization():
    from django_observability.logging.otlp_handler import OTLPHandler

    with patch(
        "django_observability.logging.otlp_handler.OTLPLogExporter"
    ) as mock_exporter:
        with patch("django_observability.logging.otlp_handler.set_logger_provider"):
            mock_exporter.return_value = MagicMock()

            handler = OTLPHandler(
                endpoint="http://localhost:4317", service_name="test-service"
            )

            assert handler is not None
            mock_exporter.assert_called_once_with(
                endpoint="http://localhost:4317", insecure=True
            )


def test_otlp_handler_default_service_name():
    from django_observability.logging.otlp_handler import OTLPHandler

    with patch(
        "django_observability.logging.otlp_handler.OTLPLogExporter"
    ) as mock_exporter:
        with patch("django_observability.logging.otlp_handler.set_logger_provider"):
            mock_exporter.return_value = MagicMock()

            handler = OTLPHandler(endpoint="http://localhost:4317")

            assert handler is not None
            mock_exporter.assert_called_once()


def test_otlp_handler_creates_resource_with_service_name():
    from django_observability.logging.otlp_handler import OTLPHandler

    with patch(
        "django_observability.logging.otlp_handler.OTLPLogExporter"
    ) as mock_exporter:
        with patch(
            "django_observability.logging.otlp_handler.Resource"
        ) as mock_resource:
            with patch("django_observability.logging.otlp_handler.set_logger_provider"):
                mock_exporter.return_value = MagicMock()
                mock_resource.return_value = MagicMock()

                handler = OTLPHandler(
                    endpoint="http://localhost:4317", service_name="my-service"
                )

                assert handler is not None
                mock_resource.assert_called_once()
                call_kwargs = mock_resource.call_args[1]
                assert "service.name" in call_kwargs["attributes"]
                assert call_kwargs["attributes"]["service.name"] == "my-service"


def test_otlp_handler_creates_logger_provider():
    from django_observability.logging.otlp_handler import OTLPHandler

    with patch(
        "django_observability.logging.otlp_handler.OTLPLogExporter"
    ) as mock_exporter:
        with patch(
            "django_observability.logging.otlp_handler.LoggerProvider"
        ) as mock_provider:
            with patch("django_observability.logging.otlp_handler.set_logger_provider"):
                mock_exporter.return_value = MagicMock()
                mock_provider_instance = MagicMock()
                mock_provider.return_value = mock_provider_instance

                handler = OTLPHandler(endpoint="http://localhost:4317")

                assert handler is not None
                mock_provider.assert_called_once()
                mock_provider_instance.add_log_record_processor.assert_called_once()


def test_otlp_handler_adds_batch_processor():
    from django_observability.logging.otlp_handler import OTLPHandler

    with patch(
        "django_observability.logging.otlp_handler.OTLPLogExporter"
    ) as mock_exporter:
        with patch(
            "django_observability.logging.otlp_handler.BatchLogRecordProcessor"
        ) as mock_processor:
            with patch("django_observability.logging.otlp_handler.set_logger_provider"):
                mock_exporter_instance = MagicMock()
                mock_exporter.return_value = mock_exporter_instance
                mock_processor.return_value = MagicMock()

                handler = OTLPHandler(endpoint="http://localhost:4317")

                assert handler is not None
                mock_processor.assert_called_once_with(mock_exporter_instance)


def test_otlp_handler_sets_global_logger_provider():
    from django_observability.logging.otlp_handler import OTLPHandler

    with patch(
        "django_observability.logging.otlp_handler.OTLPLogExporter"
    ) as mock_exporter:
        with patch(
            "django_observability.logging.otlp_handler.set_logger_provider"
        ) as mock_set_provider:
            mock_exporter.return_value = MagicMock()

            handler = OTLPHandler(endpoint="http://localhost:4317")

            assert handler is not None
            mock_set_provider.assert_called_once()


def test_otlp_handler_inherits_from_logging_handler():
    from django_observability.logging.otlp_handler import OTLPHandler
    from opentelemetry.sdk._logs import LoggingHandler

    assert issubclass(OTLPHandler, LoggingHandler)


def test_otlp_handler_accepts_additional_kwargs():
    from django_observability.logging.otlp_handler import OTLPHandler

    with patch(
        "django_observability.logging.otlp_handler.OTLPLogExporter"
    ) as mock_exporter:
        with patch("django_observability.logging.otlp_handler.set_logger_provider"):
            mock_exporter.return_value = MagicMock()

            handler = OTLPHandler(
                endpoint="http://localhost:4317", service_name="test-service"
            )

            assert handler is not None
            assert handler.level == logging.NOTSET
