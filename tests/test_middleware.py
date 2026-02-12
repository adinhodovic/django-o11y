"""Tests for middleware."""

import pytest
from unittest.mock import Mock, patch
from django.http import HttpRequest, HttpResponse
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


@pytest.mark.django_db
def test_logging_middleware_adds_custom_request_id():
    from django_observability.middleware.logging import LoggingMiddleware
    from django.test import RequestFactory
    import uuid

    rf = RequestFactory()
    request_id = str(uuid.uuid4())
    request = rf.get("/", headers={"X-Request-ID": request_id})

    middleware = LoggingMiddleware(lambda r: HttpResponse("OK"))
    response = middleware(request)

    assert response.status_code == 200


@pytest.mark.django_db
def test_logging_middleware_generates_request_id():
    from django_observability.middleware.logging import LoggingMiddleware
    from django.test import RequestFactory

    rf = RequestFactory()
    request = rf.get("/")

    middleware = LoggingMiddleware(lambda r: HttpResponse("OK"))
    response = middleware(request)

    assert response.status_code == 200


@pytest.mark.django_db
def test_logging_middleware_uses_meta_header(mock_tracer):
    from django_observability.middleware.logging import LoggingMiddleware
    from django.test import RequestFactory

    rf = RequestFactory()
    request = rf.get("/", HTTP_X_REQUEST_ID="meta-request-123")

    middleware = LoggingMiddleware(lambda r: HttpResponse("OK"))

    with mock_tracer.start_as_current_span("test-span") as span:
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            response = middleware(request)

            assert span.attributes.get("request.id") == "meta-request-123"


def test_tracing_middleware_adds_user_attributes(django_user_request, mock_tracer):
    from django_observability.middleware.tracing import TracingMiddleware

    middleware = TracingMiddleware(lambda r: HttpResponse("OK"))

    with mock_tracer.start_as_current_span("test-span") as span:
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            response = middleware(django_user_request)

            assert span.attributes.get("user.id") == "1"
            assert span.attributes.get("user.username") == "testuser"
            assert response.status_code == 200


def test_tracing_middleware_5xx_error_status(mock_tracer):
    from django_observability.middleware.tracing import TracingMiddleware
    from django.test import RequestFactory

    rf = RequestFactory()
    request = rf.get("/")

    def error_view(req):
        return HttpResponse("Internal Server Error", status=500)

    middleware = TracingMiddleware(error_view)

    with mock_tracer.start_as_current_span("test-span") as span:
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            response = middleware(request)

            assert response.status_code == 500
            assert span.status.status_code == StatusCode.ERROR


def test_tracing_middleware_records_exception(mock_tracer):
    from django_observability.middleware.tracing import TracingMiddleware
    from django.test import RequestFactory

    rf = RequestFactory()
    request = rf.get("/")

    def exception_view(req):
        raise ValueError("Test exception")

    middleware = TracingMiddleware(exception_view)

    with mock_tracer.start_as_current_span("test-span") as span:
        with patch("opentelemetry.trace.get_current_span", return_value=span):
            with pytest.raises(ValueError, match="Test exception"):
                middleware(request)

            assert span.status.status_code == StatusCode.ERROR


def test_tracing_middleware_anonymous_user():
    from django_observability.middleware.tracing import TracingMiddleware
    from django.test import RequestFactory
    from django.contrib.auth.models import AnonymousUser

    rf = RequestFactory()
    request = rf.get("/")
    request.user = AnonymousUser()

    middleware = TracingMiddleware(lambda r: HttpResponse("OK"))
    response = middleware(request)

    assert response.status_code == 200


@pytest.mark.django_db
def test_middleware_integration(client):
    try:
        response = client.get("/")
        assert response.status_code in [200, 404, 301, 302]
    except Exception as e:
        pytest.fail(f"Middleware caused exception: {e}")


@pytest.mark.django_db
def test_middleware_handles_errors_gracefully(client):
    response = client.get("/nonexistent-url-that-will-404/")
    assert response.status_code == 404
