"""Tests for security fixes: each one fails on the code as it was before the fix."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def paid_order(db):
    from orders.models import Order

    owner = User.objects.create_user(phone="09125550001", password="securepass123")
    return Order.objects.create(
        user=owner, order_number="ORD-PAID0001", shipping_address="Valiasr St, no. 12", shipping_city="Tehran",
        shipping_zip="1234567890", shipping_phone="09125550001", subtotal=100, total=100,
        payment_status=Order.PAYMENT_STATUS_PAID, status=Order.STATUS_CONFIRMED,
        payment_gateway="zarinpal", payment_authority="A0000000000000000000000000000012345", payment_ref_id="777",
    )


@pytest.mark.django_db
class TestPaymentVerifyPrivacy:
    """The verify endpoint is public: an order number alone must not reveal the order."""

    url = reverse("orders:order-pay-verify")

    def test_paid_order_is_not_shown_without_its_authority(self, paid_order):
        for authority in ("guess", "ZP-MOCK-x"):
            res = APIClient().post(self.url, {"order_number": paid_order.order_number, "authority": authority})
            assert res.status_code == 400
            assert "order" not in res.data
            assert "Valiasr" not in str(res.data)

    def test_paid_order_is_shown_again_with_its_authority(self, paid_order):
        res = APIClient().post(
            self.url, {"order_number": paid_order.order_number, "authority": paid_order.payment_authority}
        )
        assert res.status_code == 200
        assert res.data["order"]["order_number"] == paid_order.order_number
        assert res.data["ref_id"] == "777"

    def test_unknown_order_looks_like_a_wrong_authority(self, paid_order):
        unknown = APIClient().post(self.url, {"order_number": "ORD-NOPE0000", "authority": "guess"})
        wrong = APIClient().post(self.url, {"order_number": paid_order.order_number, "authority": "guess"})
        assert (unknown.status_code, unknown.data) == (wrong.status_code, wrong.data)
