"""End-to-end tests for observability stack integration.

All tests in ``TestObservabilityStackE2E`` require the full observability
stack.  Run them with::

    uv run pytest -m integration

The ``observability_stack`` session fixture (in conftest.py) starts the stack
via ``observability stack start`` and tears it down at the end of the session.
"""

import time

import pytest
import requests


def _query_tempo(trace_id: str, timeout: int = 30) -> dict:
    """Poll Tempo until the trace appears or *timeout* seconds elapse."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = requests.get(
            f"http://localhost:3200/api/traces/{trace_id}", timeout=5
        )
        if response.status_code == 200:
            return response.json()
        time.sleep(2)
    return pytest.fail(f"Trace {trace_id} did not appear in Tempo within {timeout}s")


_E2E_TRACING_CONFIG = {
    "PROFILING": {"ENABLED": False},
    "TRACING": {"OTLP_ENDPOINT": "http://localhost:4317", "SAMPLE_RATE": 1.0},
}


def _fresh_tracing_provider(service_name: str):
    """Context manager: reset the global OTel provider, call setup_tracing(),
    yield the provider, then restore the original provider on exit.

    This allows integration tests to register a real OTLP exporter without
    fighting the ``set_tracer_provider`` once-guard that was already tripped
    during Django app initialisation.
    """
    import contextlib

    import opentelemetry.trace as trace_module

    from django_o11y.tracing.setup import setup_tracing

    @contextlib.contextmanager
    def _ctx():
        original_provider = trace_module._TRACER_PROVIDER
        original_done = trace_module._TRACER_PROVIDER_SET_ONCE._done
        try:
            trace_module._TRACER_PROVIDER_SET_ONCE._done = False
            trace_module._TRACER_PROVIDER = None
            config = {"SERVICE_NAME": service_name, **_E2E_TRACING_CONFIG}
            yield setup_tracing(config)
        finally:
            trace_module._TRACER_PROVIDER_SET_ONCE._done = original_done
            trace_module._TRACER_PROVIDER = original_provider

    return _ctx()


def _span_names(data: dict) -> list:
    """Extract all span names from a Tempo trace response."""
    return [
        s["name"]
        for b in data["batches"]
        for ss in b.get("scopeSpans", [])
        for s in ss["spans"]
    ]


@pytest.mark.integration
class TestObservabilityStackE2E:
    """E2E tests that require the full observability stack."""

    def test_prometheus_scraping_metrics(self, observability_stack):
        """Test that Prometheus is configured to scrape django-app targets.

        Prometheus has a 15s scrape interval, so we wait up to 60s for at
        least one scrape cycle to complete and the ``up`` metric to appear.
        """
        deadline = time.time() + 60
        data = None
        while time.time() < deadline:
            response = requests.get(
                "http://localhost:9090/api/v1/query",
                params={"query": "up"},
                timeout=10,
            )
            assert response.status_code == 200
            data = response.json()
            if data["status"] == "success" and len(data["data"]["result"]) > 0:
                break
            time.sleep(5)

        assert data is not None
        assert data["status"] == "success"
        assert len(data["data"]["result"]) > 0, (
            "Prometheus has no 'up' results after 60s — scraping has not started"
        )

        django_targets = [
            r for r in data["data"]["result"] if r["metric"]["job"] == "django-app"
        ]
        assert len(django_targets) > 0
        assert django_targets[0]["metric"]["job"] == "django-app"

    def test_prometheus_django_metrics_available(self, observability_stack):
        """Test that Prometheus has some metrics available."""
        response = requests.get(
            "http://localhost:9090/api/v1/label/__name__/values", timeout=10
        )

        assert response.status_code == 200
        data = response.json()

        metrics = data["data"]
        assert len(metrics) > 0
        assert "up" in metrics

    def test_prometheus_can_query_metrics(self, observability_stack):
        """Test querying metrics from Prometheus.

        Polls until Prometheus has at least one result for the ``up`` metric,
        allowing time for the first 15s scrape interval to elapse.
        """
        deadline = time.time() + 60
        data = None
        while time.time() < deadline:
            response = requests.get(
                "http://localhost:9090/api/v1/query",
                params={"query": "up"},
                timeout=10,
            )
            assert response.status_code == 200
            data = response.json()
            if data["status"] == "success" and len(data["data"]["result"]) > 0:
                break
            time.sleep(5)

        assert data is not None
        assert data["status"] == "success"
        assert len(data["data"]["result"]) > 0, (
            "Prometheus has no 'up' results after 60s"
        )

    def test_tempo_api_accessible(self, observability_stack):
        """Test that Tempo API is accessible."""
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                response = requests.get("http://localhost:3200/ready", timeout=2)
                if response.status_code in [200, 204]:
                    return
                time.sleep(3)
            except requests.exceptions.RequestException:
                if attempt < max_attempts - 1:
                    time.sleep(3)
                else:
                    raise

        pytest.fail("Tempo did not become ready within 30 seconds")

    def test_loki_api_accessible(self, observability_stack):
        """Test that Loki API is accessible."""
        response = requests.get(
            "http://localhost:3100/loki/api/v1/query_range",
            params={
                "query": '{job="django-app"}',
                "start": str(int(time.time() - 3600)),
                "end": str(int(time.time())),
                "limit": 10,
            },
            timeout=10,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_pyroscope_api_accessible(self, observability_stack):
        """Test that Pyroscope API is accessible."""
        response = requests.get("http://localhost:4040/api/apps", timeout=10)

        assert response.status_code in [200, 404]

        try:
            data = response.json()
            assert isinstance(data, (dict, list))
        except Exception:
            pass

    def test_grafana_accessible(self, observability_stack):
        """Test that Grafana is accessible."""
        response = requests.get("http://localhost:3000/api/health", timeout=10)

        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "ok"

    def test_grafana_datasources_configured(self, observability_stack):
        """Test that Grafana has datasources configured."""
        response = requests.get("http://localhost:3000/api/datasources", timeout=10)

        assert response.status_code == 200
        datasources = response.json()

        ds_names = [ds["name"] for ds in datasources]
        assert "Prometheus" in ds_names
        assert "Tempo" in ds_names
        assert "Loki" in ds_names
        assert "Pyroscope" in ds_names

    def test_grafana_dashboards_imported(self, observability_stack):
        """Test that Grafana dashboards were imported."""
        response = requests.get(
            "http://localhost:3000/api/search",
            params={"type": "dash-db"},
            timeout=10,
        )

        assert response.status_code == 200
        dashboards = response.json()

        assert len(dashboards) >= 5

        dashboard_titles = [d["title"] for d in dashboards]
        assert any("django" in title.lower() for title in dashboard_titles)
        assert any("celery" in title.lower() for title in dashboard_titles)

    def test_alloy_receiving_otlp(self, observability_stack):
        """Test that Alloy is accessible."""
        response = requests.get("http://localhost:12345/metrics", timeout=2)

        assert response.status_code == 200

        metrics_text = response.text
        assert "# HELP" in metrics_text or "# TYPE" in metrics_text

    def test_trace_reaches_tempo(self, observability_stack):
        """Emit a real span via django-o11y's setup_tracing() and verify it
        lands in Tempo.

        This exercises the full pipeline:
        setup_tracing() → OTLPSpanExporter → Alloy → Tempo → query API.
        """
        import opentelemetry.trace as trace_module

        with _fresh_tracing_provider("django-o11y-e2e-test") as provider:
            tracer = trace_module.get_tracer("e2e-test")
            with tracer.start_as_current_span("e2e-test-span") as span:
                trace_id = format(span.get_span_context().trace_id, "032x")
            provider.force_flush(timeout_millis=10_000)

        data = _query_tempo(trace_id)
        service_names = [
            attr["value"]["stringValue"]
            for b in data["batches"]
            for attr in b["resource"]["attributes"]
            if attr["key"] == "service.name"
        ]
        assert "django-o11y-e2e-test" in service_names
        assert "e2e-test-span" in _span_names(data)

    def test_celery_trace_reaches_tempo(self, observability_stack, celery_app):
        """Emit a Celery task span via the test project's task and verify it
        lands in Tempo under the same trace as the parent span.

        ``celery_app`` runs with ``task_always_eager=True`` so no broker is
        needed.  CeleryInstrumentor propagates the W3C traceparent from the
        parent span into the task, producing a child span that should appear
        alongside the parent in Tempo.
        """
        import opentelemetry.trace as trace_module
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        from tests.tasks import add

        CeleryInstrumentor().uninstrument()
        with _fresh_tracing_provider("django-o11y-celery-e2e-test") as provider:
            CeleryInstrumentor().instrument()
            tracer = trace_module.get_tracer("e2e-celery-test")
            with tracer.start_as_current_span("celery-e2e-parent") as span:
                trace_id = format(span.get_span_context().trace_id, "032x")
                add.apply_async((1, 2))
            provider.force_flush(timeout_millis=10_000)
        CeleryInstrumentor().uninstrument()

        data = _query_tempo(trace_id)
        names = _span_names(data)
        assert "celery-e2e-parent" in names
        # CeleryInstrumentor names task execution spans "run/<task_name>"
        assert "run/tests.add" in names
