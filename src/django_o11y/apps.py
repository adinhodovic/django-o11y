"""Django app configuration for django-o11y."""

from importlib.metadata import PackageNotFoundError, version

from django.apps import AppConfig
from django.conf import settings

from django_o11y.logging.utils import get_logger

logger = get_logger()


class DjangoO11yConfig(AppConfig):
    """Django app configuration that sets up observability on startup."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "django_o11y"
    verbose_name = "Django O11y"
    _o11y_ready: bool = False

    def ready(self):
        """Initialize observability when Django starts."""
        from django.core.exceptions import ImproperlyConfigured

        from django_o11y.config.setup import get_o11y_config
        from django_o11y.config.utils import validate_config

        config = get_o11y_config()

        errors = validate_config(config)
        if errors:
            error_msg = (
                "Django O11y configuration errors:\n"
                + "\n".join(f"  • {error}" for error in errors)
                + "\n\nPlease fix these issues in your DJANGO_O11Y setting."
            )
            raise ImproperlyConfigured(error_msg)

        if getattr(self, "_o11y_ready", False):
            return
        self._o11y_ready = True

        self._configure_tracing(config)
        self._configure_logging(config)
        self._configure_metrics(config)
        self._configure_profiling(config)

        try:
            if settings.DEBUG:
                self._print_startup_banner(config)
        except Exception:
            pass

    def _configure_tracing(self, config: dict) -> None:
        from django_o11y.tracing.setup import setup_tracing_for_django

        setup_tracing_for_django(config)

    def _configure_logging(self, config: dict) -> None:
        from django_o11y.logging.setup import setup_logging_for_django

        setup_logging_for_django(config)

    def _configure_metrics(self, config: dict) -> None:
        from django_o11y.metrics.setup import setup_metrics_for_django

        setup_metrics_for_django(config)

    def _configure_profiling(self, config: dict) -> None:
        from django_o11y.profiling.setup import setup_profiling

        if not config.get("PROFILING", {}).get("ENABLED"):
            logger.info("Profiling disabled")
            return

        setup_profiling(config)

    def _print_startup_banner(self, config: dict) -> None:
        """Print startup banner showing enabled features."""
        try:
            try:
                pkg_version = version("django-o11y")
            except PackageNotFoundError:
                from django_o11y import __version__

                pkg_version = __version__

            banner = [
                "",
                "=" * 60,
                f"Django O11y v{pkg_version}",
                "=" * 60,
            ]

            service = config["SERVICE_NAME"]
            banner.append(f"Service: {service}")

            tracing = config["TRACING"]
            if tracing["ENABLED"]:
                endpoint = tracing["OTLP_ENDPOINT"]
                sample = tracing["SAMPLE_RATE"]
                banner.append(f"✅ Tracing → {endpoint} ({sample * 100:.0f}% sampling)")

            logging_config = config["LOGGING"]
            fmt = logging_config["FORMAT"]
            banner.append(f"✅ Logging → format={fmt}")

            metrics_config = config["METRICS"]
            if metrics_config["PROMETHEUS_ENABLED"]:
                endpoint = metrics_config["PROMETHEUS_ENDPOINT"]
                banner.append(f"✅ Metrics → {endpoint}")

            if config["CELERY"]["ENABLED"]:
                banner.append("✅ Celery → auto-instrumented")

            profiling = config["PROFILING"]
            if profiling["ENABLED"]:
                url = profiling["PYROSCOPE_URL"]
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
