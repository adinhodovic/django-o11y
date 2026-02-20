"""Django app configuration for django-o11y."""

import logging
from importlib.metadata import PackageNotFoundError, version

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger("django_o11y")


class DjangoO11yConfig(AppConfig):
    """Django app configuration that sets up observability on startup."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_o11y"
    verbose_name = "Django O11y"
    _o11y_ready: bool = False

    def ready(self):
        """Initialize observability when Django starts."""
        from django.core.exceptions import ImproperlyConfigured

        from django_o11y.conf import get_o11y_config
        from django_o11y.instrumentation.setup import setup_instrumentation
        from django_o11y.profiling import setup_profiling
        from django_o11y.tracing.provider import setup_tracing
        from django_o11y.validation import validate_config

        config = get_o11y_config()

        errors = validate_config(config)
        if errors:
            error_msg = (
                "Django O11y configuration errors:\n"
                + "\n".join(f"  • {error}" for error in errors)
                + "\n\nPlease fix these issues in your DJANGO_O11Y setting."
            )
            raise ImproperlyConfigured(error_msg)

        # Prevent double initialisation. AppConfig.ready() can be called more
        # than once in some environments (e.g. Django's runserver reloader).
        if getattr(self, "_o11y_ready", False):
            return
        self._o11y_ready = True

        # Sync METRICS.EXPORT_MIGRATIONS into the django-prometheus setting it
        # reads directly. We always set it so our config is the single source
        # of truth, overriding whatever the user may have set elsewhere.
        settings.PROMETHEUS_EXPORT_MIGRATIONS = config["METRICS"]["EXPORT_MIGRATIONS"]

        if config["TRACING"]["ENABLED"]:
            setup_tracing(config)
        else:
            logger.info("Tracing disabled")

        setup_instrumentation(config)

        logging_config = config.get("LOGGING", {})
        fmt = logging_config.get("FORMAT", "console")
        logger.info("Logging configured, format=%s", fmt)

        metrics_config = config.get("METRICS", {})
        if metrics_config.get("PROMETHEUS_ENABLED", True):
            endpoint = metrics_config.get("PROMETHEUS_ENDPOINT", "/metrics")
            logger.info("Metrics enabled at %s", endpoint)

        if config.get("PROFILING", {}).get("ENABLED"):
            setup_profiling(config)
        else:
            logger.info("Profiling disabled")

        try:
            if settings.DEBUG:
                self._print_startup_banner(config)
        except Exception:
            pass

    def _print_startup_banner(self, config: dict) -> None:
        """Print startup banner showing enabled features."""
        try:
            try:
                pkg_version = version("django-o11y")
            except PackageNotFoundError:
                pkg_version = "0.1.1"

            banner = [
                "",
                "=" * 60,
                f"Django O11y v{pkg_version}",
                "=" * 60,
            ]

            service = config.get("SERVICE_NAME", "unknown")
            banner.append(f"Service: {service}")

            tracing = config.get("TRACING", {})
            if tracing.get("ENABLED"):
                endpoint = tracing.get("OTLP_ENDPOINT", "")
                sample = tracing.get("SAMPLE_RATE", 1.0)
                banner.append(f"✅ Tracing → {endpoint} ({sample * 100:.0f}% sampling)")

            logging_config = config.get("LOGGING", {})
            fmt = logging_config.get("FORMAT", "console")
            banner.append(f"✅ Logging → format={fmt}")

            metrics_config = config.get("METRICS", {})
            if metrics_config.get("PROMETHEUS_ENABLED", True):
                endpoint = metrics_config.get("PROMETHEUS_ENDPOINT", "/metrics")
                banner.append(f"✅ Metrics → {endpoint}")

            if config.get("CELERY", {}).get("ENABLED"):
                banner.append("✅ Celery → auto-instrumented")

            profiling = config.get("PROFILING", {})
            if profiling.get("ENABLED"):
                url = profiling.get("PYROSCOPE_URL", "")
                banner.append(f"✅ Profiling → {url}")

            banner.extend(
                [
                    "",
                    "=" * 60,
                    "",
                ]
            )

            print("\n".join(banner))
        except Exception:
            pass
