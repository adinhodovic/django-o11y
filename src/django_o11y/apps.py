"""Django app configuration for django-o11y."""

import logging
import os
import sys
from importlib.metadata import PackageNotFoundError, version

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger("django_o11y")


def _is_celery_prefork_worker_boot() -> bool:
    """Return True for `celery worker` booting with prefork pool.

    Celery defaults to prefork when no explicit pool is passed.
    """
    args = sys.argv

    if "worker" not in args:
        return False

    if not args:
        return False

    cmd = os.path.basename(args[0])
    is_celery_command = cmd == "celery"
    is_python_module_celery = any(
        arg == "-m" and idx + 1 < len(args) and args[idx + 1] == "celery"
        for idx, arg in enumerate(args)
    )

    if not (is_celery_command or is_python_module_celery):
        return False

    for idx, arg in enumerate(args):
        if arg.startswith("--pool="):
            return arg.split("=", 1)[1] == "prefork"
        if arg in {"-P", "--pool"} and idx + 1 < len(args):
            return args[idx + 1] == "prefork"

    return True


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

        defer_tracing_for_celery_prefork = _is_celery_prefork_worker_boot()
        self._configure_tracing(config, defer_tracing_for_celery_prefork)
        self._configure_instrumentation_and_metrics(config)
        self._configure_profiling(config, defer_tracing_for_celery_prefork)

        try:
            if settings.DEBUG:
                self._print_startup_banner(config)
        except Exception:
            pass

    def _configure_tracing(self, config: dict, defer_for_celery_prefork: bool) -> None:
        from django_o11y.tracing.provider import setup_tracing

        if config["TRACING"]["ENABLED"] and not defer_for_celery_prefork:
            setup_tracing(config)
            from django_o11y.fork import register_post_fork_handler

            register_post_fork_handler()
            return

        if config["TRACING"]["ENABLED"]:
            logger.info(
                "Tracing deferred for Celery prefork worker boot; "
                "initialising per child process"
            )
            return

        logger.info("Tracing disabled")

    def _configure_instrumentation_and_metrics(self, config: dict) -> None:
        from django_o11y.instrumentation.setup import setup_instrumentation

        setup_instrumentation(config)

        fmt = config.get("LOGGING", {}).get("FORMAT", "console")
        logger.info("Logging configured, format=%s", fmt)

        metrics = config.get("METRICS", {})
        if metrics.get("PROMETHEUS_ENABLED", True):
            logger.info(
                "Metrics enabled at %s", metrics.get("PROMETHEUS_ENDPOINT", "/metrics")
            )

    def _configure_profiling(
        self, config: dict, defer_for_celery_prefork: bool
    ) -> None:
        from django_o11y.profiling import setup_profiling

        if config.get("PROFILING", {}).get("ENABLED") and not defer_for_celery_prefork:
            setup_profiling(config)
            return

        if config.get("PROFILING", {}).get("ENABLED"):
            logger.info("Profiling deferred for Celery prefork worker boot")
            return

        logger.info("Profiling disabled")

    def _print_startup_banner(self, config: dict) -> None:
        """Print startup banner showing enabled features."""
        try:
            try:
                pkg_version = version("django-o11y")
            except PackageNotFoundError:
                pkg_version = "0.2.6"

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
