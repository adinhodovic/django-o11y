"""Tests for logging setup helpers."""

from unittest.mock import patch

from django.test import override_settings

from tests.conftest import make_config


@override_settings(DJANGO_STRUCTLOG_CELERY_ENABLED=False)
def test_setup_logging_enables_django_structlog_celery_for_web_app():
    from django.conf import settings

    from django_o11y.logging.setup import setup_logging_for_django

    config = make_config({"CELERY": {"ENABLED": True}})

    with patch("importlib.import_module") as mock_import:
        setup_logging_for_django(config)

    assert settings.DJANGO_STRUCTLOG_CELERY_ENABLED is True
    mock_import.assert_called_once_with("django_o11y.logging.signals")


@override_settings(DJANGO_STRUCTLOG_CELERY_ENABLED=False)
def test_setup_logging_does_not_toggle_structlog_celery_when_celery_disabled():
    from django.conf import settings

    from django_o11y.logging.setup import setup_logging_for_django

    config = make_config({"CELERY": {"ENABLED": False}})

    with patch("importlib.import_module") as mock_import:
        setup_logging_for_django(config)

    assert settings.DJANGO_STRUCTLOG_CELERY_ENABLED is False
    mock_import.assert_not_called()


@override_settings(DJANGO_STRUCTLOG_CELERY_ENABLED=False)
def test_setup_logging_does_not_toggle_structlog_celery_when_celery_logging_disabled():
    from django.conf import settings

    from django_o11y.logging.setup import setup_logging_for_django

    config = make_config({"CELERY": {"ENABLED": True, "LOGGING_ENABLED": False}})

    with patch("importlib.import_module") as mock_import:
        setup_logging_for_django(config)

    assert settings.DJANGO_STRUCTLOG_CELERY_ENABLED is False
    mock_import.assert_not_called()
