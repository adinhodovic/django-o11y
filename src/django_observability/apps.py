"""Django app configuration for django-observability."""

from django.apps import AppConfig


class DjangoObservabilityConfig(AppConfig):
    """Django app configuration that sets up observability on startup."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_observability"
    verbose_name = "Django Observability"

    def ready(self):
        """Initialize observability when Django starts."""
        from django.core.exceptions import ImproperlyConfigured

        from django_observability.conf import get_observability_config
        from django_observability.instrumentation.setup import setup_instrumentation
        from django_observability.logging.config import setup_logging
        from django_observability.profiling import setup_profiling
        from django_observability.tracing.provider import setup_tracing
        from django_observability.validation import validate_config

        config = get_observability_config()

        errors = validate_config(config)
        if errors:
            error_msg = (
                "Django Observability configuration errors:\n"
                + "\n".join(f"  • {error}" for error in errors)
                + "\n\nPlease fix these issues in your DJANGO_OBSERVABILITY setting."
            )
            raise ImproperlyConfigured(error_msg)

        if config["TRACING"]["ENABLED"]:
            setup_tracing(config)

        if config["LOGGING"]["ENABLED"]:
            setup_logging(config)

        setup_instrumentation(config)

        if config.get("PROFILING", {}).get("ENABLED"):
            setup_profiling(config)

        try:
            from django.conf import settings

            if settings.DEBUG:
                self._print_startup_banner(config)
        except Exception:
            pass

    def _print_startup_banner(self, config: dict) -> None:
        """Print startup banner showing enabled features."""
        try:
            try:
                from importlib.metadata import version

                pkg_version = version("django-observability")
            except Exception:
                pkg_version = "0.1.0"

            banner = [
                "",
                "=" * 60,
                f"Django Observability v{pkg_version}",
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
            if logging_config.get("ENABLED"):
                fmt = logging_config.get("FORMAT", "console")
                colorized = logging_config.get("COLORIZED", False)
                fmt_str = f"{fmt} format"
                if colorized:
                    fmt_str += " (colorized)"
                banner.append(f"✅ Logging → {fmt_str}")

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
                    "Health Check: python manage.py observability check",
                    "=" * 60,
                    "",
                ]
            )

            print("\n".join(banner))
        except Exception:
            pass
