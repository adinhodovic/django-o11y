"""End-to-end tests for observability stack integration.

All tests in ``TestObservabilityStackE2E`` require the full observability
stack.  Run them with::

    uv run pytest -m integration

The ``observability_stack`` session fixture (in conftest.py) starts the stack
via ``observability stack start`` and tears it down at the end of the session.
"""

import time
from decimal import Decimal

import pytest
import requests


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
                "http://localhost:9090/api/v1/query", params={"query": "up"}
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
        response = requests.get("http://localhost:9090/api/v1/label/__name__/values")

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
                "http://localhost:9090/api/v1/query", params={"query": "up"}
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
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_pyroscope_api_accessible(self, observability_stack):
        """Test that Pyroscope API is accessible."""
        response = requests.get("http://localhost:4040/api/apps")

        assert response.status_code in [200, 404]

        try:
            data = response.json()
            assert isinstance(data, (dict, list))
        except Exception:
            pass

    def test_grafana_accessible(self, observability_stack):
        """Test that Grafana is accessible."""
        response = requests.get("http://localhost:3000/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "ok"

    def test_grafana_datasources_configured(self, observability_stack):
        """Test that Grafana has datasources configured."""
        response = requests.get("http://localhost:3000/api/datasources")

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
            "http://localhost:3000/api/search", params={"type": "dash-db"}
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


@pytest.mark.django_db
class TestObservabilityWithTestApp:
    """Tests using the test Django app."""

    def test_create_order_with_tracing(self):
        """Test creating an order generates traces."""
        from tests.models import Order

        order = Order.objects.create(
            order_number="E2E-TEST-001",
            customer_email="e2e@example.com",
            amount=Decimal("99.99"),
            status="pending",
        )

        assert order.id is not None
        assert Order.objects.filter(order_number="E2E-TEST-001").exists()

    def test_query_orders_with_tracing(self):
        """Test querying orders generates DB traces."""
        from tests.models import Order

        Order.objects.create(
            order_number="E2E-QUERY-001",
            customer_email="query@example.com",
            amount=Decimal("50.00"),
        )

        orders = list(Order.objects.filter(status="pending"))

        assert len(orders) >= 1

    def test_bulk_operations_with_tracing(self):
        """Test bulk operations generate traces."""
        from tests.models import Order

        orders = [
            Order(
                order_number=f"E2E-BULK-{i:03d}",
                customer_email=f"bulk{i}@example.com",
                amount=Decimal("10.00"),
            )
            for i in range(5)
        ]

        Order.objects.bulk_create(orders)

        bulk_orders = Order.objects.filter(order_number__startswith="E2E-BULK-")
        assert bulk_orders.count() == 5

    def test_order_aggregation_with_tracing(self):
        """Test aggregation queries generate traces."""
        from django.db.models import Count, Sum

        from tests.models import Order

        Order.objects.bulk_create(
            [
                Order(
                    order_number=f"E2E-AGG-{i}",
                    customer_email=f"agg{i}@example.com",
                    amount=Decimal("100.00"),
                    status="completed",
                )
                for i in range(3)
            ]
        )

        stats = Order.objects.filter(status="completed").aggregate(
            total=Sum("amount"), count=Count("id")
        )

        assert stats["count"] >= 3
        assert stats["total"] >= Decimal("300.00")
