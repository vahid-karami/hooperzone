import io

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.management.commands.setup_roles import PRODUCT_EDITORS
from products.models import Category, Product

User = get_user_model()

SHOP_URL_NAMES = ["orders:admin-stats", "orders:admin-order-list", "orders:admin-settings", "accounts:admin-customers"]


@pytest.fixture
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def _png():
    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (20, 20), "navy").save(buf, "PNG")
    return SimpleUploadedFile("p.png", buf.getvalue(), content_type="image/png")


@pytest.fixture
def catalog(db):
    call_command("setup_roles", stdout=io.StringIO())
    cat = Category.objects.create(name="Knee", slug="knee")
    Product.objects.create(category=cat, name="Brace", slug="brace", description="d", price=100, stock=3)
    return cat


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def product_editor():
    user = User.objects.create_user(phone="09125550000", password="securepass123", is_staff=True)
    user.groups.add(Group.objects.get(name=PRODUCT_EDITORS))
    return User.objects.get(pk=user.pk)  # fresh instance: permissions are cached per object


def test_setup_roles_is_idempotent(catalog):
    call_command("setup_roles", stdout=io.StringIO())
    group = Group.objects.get(name=PRODUCT_EDITORS)
    codenames = set(group.permissions.values_list("codename", flat=True))
    assert {"add_product", "change_product", "change_category", "delete_productimage"} <= codenames
    assert "delete_product" not in codenames and "delete_category" not in codenames


def test_product_editor_manages_the_catalog(catalog, media):
    client = client_for(product_editor())
    assert client.get(reverse("products:admin-product-list")).status_code == status.HTTP_200_OK
    res = client.post(
        reverse("products:admin-product-list"),
        {"name": "Sleeve", "description": "d", "price": 50, "stock": 2, "category": catalog.id},
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED, res.data
    detail = reverse("products:admin-product-detail", kwargs={"slug": "brace"})
    assert client.patch(detail, {"price": 120}, format="json").status_code == status.HTTP_200_OK

    images = reverse("products:admin-product-images", kwargs={"slug": "brace"})
    image_id = client.post(images, {"image": _png()}, format="multipart").data[0]["id"]
    image = reverse("products:admin-product-image-detail", kwargs={"slug": "brace", "image_id": image_id})
    assert client.delete(image).status_code == status.HTTP_200_OK  # removing a photo is allowed

    category = reverse("products:admin-category-detail", kwargs={"slug": "knee"})
    assert client.patch(category, {"name_fa": "زانو"}, format="json").status_code == status.HTTP_200_OK


def test_product_editor_cannot_delete_products_or_categories(catalog):
    client = client_for(product_editor())
    assert client.delete(reverse("products:admin-product-detail", kwargs={"slug": "brace"})).status_code == 403
    bulk = reverse("products:admin-product-bulk-action")
    res = client.post(bulk, {"slugs": ["brace"], "action": "delete"}, format="json")
    assert res.status_code == status.HTTP_403_FORBIDDEN
    assert client.delete(reverse("products:admin-category-detail", kwargs={"slug": "knee"})).status_code == 403
    assert Product.objects.filter(slug="brace").exists()


def test_product_editor_cannot_see_orders_customers_or_settings(catalog):
    client = client_for(product_editor())
    for url in map(reverse, SHOP_URL_NAMES):
        assert client.get(url).status_code == status.HTTP_403_FORBIDDEN, url


def test_staff_without_a_group_has_no_portal_access(catalog):
    client = client_for(User.objects.create_user(phone="09125551111", password="securepass123", is_staff=True))
    assert client.get(reverse("products:admin-product-list")).status_code == status.HTTP_403_FORBIDDEN
    for url in map(reverse, SHOP_URL_NAMES):
        assert client.get(url).status_code == status.HTTP_403_FORBIDDEN, url


def test_group_without_staff_status_has_no_access(catalog):
    user = User.objects.create_user(phone="09125552222", password="securepass123")
    user.groups.add(Group.objects.get(name=PRODUCT_EDITORS))
    assert client_for(user).get(reverse("products:admin-product-list")).status_code == status.HTTP_403_FORBIDDEN


def test_profile_reports_admin_access(catalog):
    owner = User.objects.create_superuser(phone="09125553333", password="securepass123")
    customer = User.objects.create_user(phone="09125554444", password="securepass123")
    access = lambda user: client_for(user).get(reverse("accounts:profile")).data["admin_access"]  # noqa: E731
    assert access(owner) == {"catalog": True, "shop": True}
    assert access(product_editor()) == {"catalog": True, "shop": False}
    assert access(customer) == {"catalog": False, "shop": False}


def test_admin_without_slash_redirects(client):
    res = client.get("/admin")
    assert res.status_code == 301 and res["Location"] == "/admin/"
