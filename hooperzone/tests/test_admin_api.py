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
    assert [o["order_number"] for o in client.get(url, {"payment_status": "paid"}).data["results"]] == ["ORD-PAID"]
    assert [o["order_number"] for o in client.get(url, {"search": "unpaid"}).data["results"]] == ["ORD-UNPAID"]
    item = client.get(url, {"status": "confirmed"}).data["results"][0]["items"][0]
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


def test_order_list_is_paginated(shop):
    client = shop["client"]
    for i in range(30):
        Order.objects.create(
            user=shop["customer"], order_number=f"ORD-P{i:03d}", shipping_address="x", shipping_city="Tehran",
            shipping_zip="1", shipping_phone="0912", subtotal=1, total=1,
        )
    data = client.get(reverse("orders:admin-order-list"), {"page_size": 10, "page": 2}).data
    assert data["count"] == 32
    assert len(data["results"]) == 10
    assert data["next"] and data["previous"]


def test_status_moves_forward_only_and_saves_tracking(shop):
    client = shop["client"]
    url = reverse("orders:admin-order-update", kwargs={"order_number": "ORD-PAID"})
    res = client.patch(url, {"status": "shipped", "tracking_code": "123456789012345678"}, format="json")
    assert res.status_code == 200
    assert res.data["tracking_code"] == "123456789012345678"
    assert client.patch(url, {"status": "confirmed"}).status_code == status.HTTP_400_BAD_REQUEST
    assert client.patch(url, {"status": "delivered"}).data["status"] == "delivered"
    # A delivered order can't be cancelled (and restocked) from the portal.
    assert client.patch(url, {"status": "cancelled"}).status_code == status.HTTP_400_BAD_REQUEST
    assert client.get(url).data["order_number"] == "ORD-PAID"


def test_bulk_status(shop):
    res = shop["client"].post(
        reverse("orders:admin-order-bulk-status"),
        {"order_numbers": ["ORD-PAID", "ORD-UNPAID", "ORD-NOPE"], "status": "processing"},
        format="json",
    )
    assert sorted(res.data["updated"]) == ["ORD-PAID", "ORD-UNPAID"]
    assert res.data["skipped"][0]["order_number"] == "ORD-NOPE"


def test_order_export_csv_has_bom_and_rows(shop):
    res = shop["client"].get(reverse("orders:admin-order-export"), {"payment_status": "paid"})
    assert res["Content-Type"].startswith("text/csv")
    body = res.content.decode("utf-8")
    assert body.startswith("﻿")
    assert "ORD-PAID" in body and "ORD-UNPAID" not in body


def test_shop_settings_roundtrip(shop):
    url = reverse("orders:admin-settings")
    res = shop["client"].patch(url, {"shipping_tipax": 175000, "store_phone": "021-1234"}, format="json")
    assert res.status_code == 200
    assert shop["client"].get(url).data["shipping_tipax"] == 175000
    assert APIClient().get(reverse("orders:shop-info")).data["store_phone"] == "021-1234"


def test_stats_include_range_and_best_sellers(shop):
    data = shop["client"].get(reverse("orders:admin-stats"), {"days": 30}).data
    assert len(data["last_7_days"]) == 30
    assert data["best_sellers"][0]["slug"] == "brace"
    assert data["best_sellers"][0]["quantity"] == 2
    assert data["average_order_value"] == 200


def test_customers_list_and_export(shop):
    client = shop["client"]
    data = client.get(reverse("accounts:admin-customers"), {"search": "Ali"}).data
    assert data["count"] == 1
    row = data["results"][0]
    assert row["order_count"] == 2 and row["paid_order_count"] == 1 and float(row["total_spent"]) == 200
    assert "09121110000" in client.get(reverse("accounts:admin-customers-export")).content.decode()


@pytest.fixture
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def _png():
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "navy").save(buf, "PNG")
    return SimpleUploadedFile("p.png", buf.getvalue(), content_type="image/png")


def test_product_images_upload_primary_delete(shop, media):
    client = shop["client"]
    url = reverse("products:admin-product-images", kwargs={"slug": "brace"})
    first = client.post(url, {"image": _png()}, format="multipart")
    assert first.status_code == 200, first.data
    assert first.data[0]["is_primary"] is True
    second = client.post(url, {"image": _png()}, format="multipart").data
    assert len(second) == 2
    new_id = [i["id"] for i in second if not i["is_primary"]][0]
    detail = reverse("products:admin-product-image-detail", kwargs={"slug": "brace", "image_id": new_id})
    res = client.patch(detail, {"is_primary": "true", "alt_text": "زانوبند"}, format="json")
    assert res.data[0]["id"] == new_id and res.data[0]["alt_text"] == "زانوبند"
    res = client.delete(detail)
    assert len(res.data) == 1 and res.data[0]["is_primary"] is True


def test_category_crud(shop, media):
    client = shop["client"]
    url = reverse("products:admin-category-list")
    res = client.post(url, {"name": "Ankle", "name_fa": "مچ پا", "image": _png()}, format="multipart")
    assert res.status_code == 201, res.data
    assert res.data["slug"] == "ankle"
    detail = reverse("products:admin-category-detail", kwargs={"slug": "ankle"})
    assert client.patch(detail, {"is_active": False}, format="json").data["is_active"] is False
    assert {c["slug"] for c in client.get(url).data} == {"knee", "ankle"}
    # A category that still has products can't be deleted.
    knee = reverse("products:admin-category-detail", kwargs={"slug": "knee"})
    assert client.delete(knee).status_code == 400
    assert client.delete(detail).status_code == 204


def test_product_bulk_actions(shop):
    from products.models import Product

    client = shop["client"]
    spare = Product.objects.create(category=shop["product"].category, name="Spare", slug="spare", description="d", price=1)
    url = reverse("products:admin-product-bulk-action")
    assert client.post(url, {"slugs": ["brace", "spare"], "action": "feature"}, format="json").data["updated_count"] == 2
    client.post(url, {"slugs": ["brace", "spare"], "action": "delete"}, format="json")
    # The ordered product is kept (deactivated) for order history; the other is gone.
    assert Product.objects.get(slug="brace").is_active is False
    assert not Product.objects.filter(pk=spare.pk).exists()


def test_product_admin_list_is_paginated_and_exports(shop):
    client = shop["client"]
    data = client.get(reverse("products:admin-product-list"), {"page_size": 5}).data
    assert data["count"] == 1 and data["results"][0]["slug"] == "brace"
    assert "brace" in client.get(reverse("products:admin-product-export")).content.decode()


def test_new_admin_endpoints_require_staff(shop):
    client = APIClient()
    client.force_authenticate(shop["customer"])
    for name in ["orders:admin-settings", "orders:admin-order-export", "accounts:admin-customers",
                 "products:admin-category-list", "products:admin-product-export"]:
        assert client.get(reverse(name)).status_code == status.HTTP_403_FORBIDDEN, name
