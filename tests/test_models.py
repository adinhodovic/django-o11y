"""Tests for test models."""

from decimal import Decimal

import pytest


@pytest.mark.django_db
def test_order_creation():
    """Test creating an Order model."""
    from tests.models import Order

    order = Order.objects.create(
        order_number="TEST-001",
        customer_email="test@example.com",
        amount=Decimal("99.99"),
    )

    assert order.id is not None
    assert order.order_number == "TEST-001"
    assert order.customer_email == "test@example.com"
    assert order.amount == Decimal("99.99")
    assert order.status == "pending"  # Default status


@pytest.mark.django_db
def test_order_status_choices():
    """Test Order status field choices."""
    from tests.models import Order

    statuses = ["pending", "processing", "completed", "failed"]

    for status in statuses:
        order = Order.objects.create(
            order_number=f"TEST-{status}",
            customer_email=f"{status}@example.com",
            amount=Decimal("10.00"),
            status=status,
        )
        assert order.status == status


@pytest.mark.django_db
def test_order_unique_order_number():
    """Test that order_number must be unique."""
    from django.db import IntegrityError

    from tests.models import Order

    Order.objects.create(
        order_number="UNIQUE-001",
        customer_email="test1@example.com",
        amount=Decimal("50.00"),
    )

    with pytest.raises(IntegrityError):
        Order.objects.create(
            order_number="UNIQUE-001",
            customer_email="test2@example.com",
            amount=Decimal("75.00"),
        )


@pytest.mark.django_db
def test_order_str_representation():
    """Test Order __str__ method."""
    from tests.models import Order

    order = Order.objects.create(
        order_number="STR-001",
        customer_email="str@example.com",
        amount=Decimal("25.50"),
        status="processing",
    )

    assert str(order) == "Order STR-001 - processing"


@pytest.mark.django_db
def test_order_ordering():
    """Test that orders are ordered by created_at descending."""
    import time

    from tests.models import Order

    order1 = Order.objects.create(
        order_number="ORD-001",
        customer_email="test1@example.com",
        amount=Decimal("10.00"),
    )

    time.sleep(0.01)

    order2 = Order.objects.create(
        order_number="ORD-002",
        customer_email="test2@example.com",
        amount=Decimal("20.00"),
    )

    orders = list(Order.objects.all())

    assert orders[0].id == order2.id
    assert orders[1].id == order1.id
