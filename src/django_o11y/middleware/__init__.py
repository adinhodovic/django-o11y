"""Middleware for django-o11y."""

from django_o11y.middleware.logging import LoggingMiddleware
from django_o11y.middleware.tracing import TracingMiddleware

__all__ = ["LoggingMiddleware", "TracingMiddleware"]
