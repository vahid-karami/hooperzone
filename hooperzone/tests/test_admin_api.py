import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from orders.models import Order, OrderItem
from products.models import Category, Product

User = get_user_model()


@pytest.fixture
def shop(db):
    cat = Category.objects.create(name="Knee", slug="knee")
    product = Product.objects.create(category=cat, name="Brace", slug="brace", description="d", price=100, stock=3)
    customer = User.objects.create_user(phone="09121110000", password="securepass123", first_name="Ali")
    paid = Order.objects.create(
        user=customer, order_number="ORD-PAID", shipping_address="x", shipping_city="Tehran", shipping_zip="1",
        shipping_phone="0912", subtotal=200, total=200, status=Order.STATUS_CONFIRMED,
        payment_status=Order.PAYMENT_STATUS_PAID,
    )
    OrderItem.objects.create(order=paid, product=product, product_name="Brace", product_price=100, quantity=2)
    Order.objects.create(
        user=customer, order_number="ORD-UNPAID", shipping_address="x", shipping_city="Tehran", shipping_zip="1",
        shipping_phone="0912", subtotal=100, total=100,
    )
    staff = User.objects.create_user(phone="09129990000", password="securepass123", is_staff=True)
    client = APIClient()
    client.force_authenticate(staff)
    return {"client": client, "customer": customer, "product": product, "paid": paid}


def test_admin_endpoints_require_staff(shop):
    client = APIClient()
    client.force_authenticate(shop["customer"])
    assert client.get(reverse("orders:admin-stats")).status_code == status.HTTP_403_FORBIDDEN
    assert client.get(reverse("orders:admin-order-list")).status_code == status.HTTP_403_FORBIDDEN
    res = client.patch(reverse("orders:admin-order-update", kwargs={"order_number": "ORD-PAID"}), {"status": "shipped"})
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_admin_stats(shop):
    data = shop["client"].get(reverse("orders:admin-stats")).data
    assert float(data["revenue_total"]) == 200
    assert data["orders_total"] == 2
    assert data["awaiting_payment"] == 1
    assert data["to_ship"] == 1
    assert data["customers"] == 1
    assert data["low_stock"][0]["slug"] == "brace"
    assert len(data["last_7_days"]) == 7
    assert data["recent_orders"][0]["customer"]["name"] == "Ali"


def test_admin_order_list_filters(shop):
    client = shop["client"]
    url = reverse("orders:admin-order-list")
    assert [o["order_number"] for o in client.get(url, {"payment_status": "paid"}).data] == ["ORD-PAID"]
    assert [o["order_number"] for o in client.get(url, {"search": "unpaid"}).data] == ["ORD-UNPAID"]
    item = client.get(url, {"status": "confirmed"}).data[0]["items"][0]
    assert item["product_slug"] == "brace"


def test_admin_status_update_and_cancel_restocks(shop):
    client = shop["client"]
    url = reverse("orders:admin-order-update", kwargs={"order_number": "ORD-PAID"})
    assert client.patch(url, {"status": "bogus"}).status_code == status.HTTP_400_BAD_REQUEST
    assert client.patch(url, {"status": "shipped"}).data["status"] == "shipped"

    assert client.patch(url, {"status": "cancelled"}).status_code == status.HTTP_200_OK
    shop["product"].refresh_from_db()
    assert shop["product"].stock == 5  # 3 + 2 returned
    assert client.patch(url, {"status": "processing"}).status_code == status.HTTP_400_BAD_REQUEST
