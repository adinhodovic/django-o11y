"""Django app configuration for django-o11y."""

import os
from importlib.metadata import PackageNotFoundError, version

from django.apps import AppConfig
from django.conf import settings


class DjangoO11yConfig(AppConfig):
    """Django app configuration that sets up observability on startup."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_o11y"
    verbose_name = "Django O11y"

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

        # runserver spawns a reloader process and a worker process, both calling
        # ready(). Django sets DJANGO_AUTORELOAD_ENV in the reloader process;
        # skip setup there to avoid double initialisation and a duplicate banner.
        if os.environ.get("DJANGO_AUTORELOAD_ENV"):
            return

        if config["TRACING"]["ENABLED"]:
            setup_tracing(config)

        setup_instrumentation(config)

        if config.get("PROFILING", {}).get("ENABLED"):
            setup_profiling(config)

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
                pkg_version = "0.1.0"

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

            if config.get("CELERY", {}).get("ENABLED"):
                banner.append("✅ Celery → auto-instrumented")

            profiling = config.get("PROFILING", {})
            if profiling.get("ENABLED"):
                url = profiling.get("PYROSCOPE_URL", "")
                banner.append(f"✅ Profiling → {url}")
            else:
                banner.append("⚠️  Profiling → disabled")

            banner.extend(
                [
                    "",
                    "Metrics: /metrics",
                    "Health Check: python manage.py o11y check",
                    "=" * 60,
                    "",
                ]
            )

            print("\n".join(banner))
        except Exception:
            pass
