"""Prometheus metrics for the test project."""

from django_o11y.metrics.utils import counter

tasks_total = counter(
    "tests_tasks_total",
    "Total number of test tasks executed",
    labelnames=["task_name"],
)
