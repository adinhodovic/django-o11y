"""Middleware for django-observability."""

from django_observability.middleware.logging import LoggingMiddleware
from django_observability.middleware.tracing import TracingMiddleware

__all__ = ["LoggingMiddleware", "TracingMiddleware"]
