"""Celery logging signal handlers."""

from celery.signals import setup_logging

from django_o11y.utils.signals import connect_signal


@connect_signal(setup_logging, dispatch_uid="django_o11y.logging.setup_logging")
def _config_loggers(*args, **kwargs):  # pylint: disable=unused-variable
    """Apply Django ``LOGGING`` config to Celery worker logging."""
    import logging.config as _logging_config

    from django.conf import settings

    if hasattr(settings, "LOGGING") and settings.LOGGING:
        _logging_config.dictConfig(settings.LOGGING)
        return True
    return False
