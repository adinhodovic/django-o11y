"""OTLP logging handler for exporting logs to OpenTelemetry collectors."""

import logging
from typing import Any

from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource


class OTLPHandler(LoggingHandler):
    """
    Logging handler that exports logs to an OTLP endpoint.

    This bridges Python logging (including structlog) to OpenTelemetry logs.
    """

    def __init__(self, endpoint: str, service_name: str = "django-app", **kwargs: Any):
        """
        Initialize OTLP logging handler.

        Args:
            endpoint: OTLP endpoint URL (e.g., "http://localhost:4317")
            service_name: Service name for the logs
            **kwargs: Additional arguments passed to LoggingHandler
        """
        resource = Resource(attributes={SERVICE_NAME: service_name})
        logger_provider = LoggerProvider(resource=resource)

        otlp_exporter = OTLPLogExporter(endpoint=endpoint, insecure=True)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))

        set_logger_provider(logger_provider)
        super().__init__(level=logging.NOTSET, logger_provider=logger_provider)
