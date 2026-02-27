"""Test models for django-o11y test suite."""

from django.db import models
from django_prometheus.models import ExportModelOperationsMixin


class Order(ExportModelOperationsMixin("order"), models.Model):
    """Sample order model for testing database tracing.

    Created by the Django web process on each /trigger/ request, so
    django_model_inserts_total{model="order"} reflects web process activity.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    order_number = models.CharField(max_length=50, unique=True)
    customer_email = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.order_number} - {self.status}"


class TaskResult(ExportModelOperationsMixin("taskresult"), models.Model):
    """Records the result of a Celery task execution.

    Created exclusively by the Celery worker, so
    django_model_inserts_total{model="taskresult"} reflects worker activity.
    """

    task_id = models.CharField(max_length=255, unique=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="results")
    result = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"TaskResult {self.task_id} = {self.result}"
