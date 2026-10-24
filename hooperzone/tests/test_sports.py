import io

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from products.models import Category, Product, Sport

User = get_user_model()


@pytest.fixture
def catalog(db):
    cat = Category.objects.create(name="Supports", slug="supports")
    knee = Product.objects.create(category=cat, name="Knee", slug="knee", description="d", price=10, injury_type="knee")
    elbow = Product.objects.create(category=cat, name="Elbow", slug="elbow", description="d", price=10, injury_type="elbow")
    hidden = Product.objects.create(
        category=cat, name="Old", slug="old", description="d", price=10, injury_type="knee", is_active=False
    )
    running = Sport.objects.create(name="Running", name_fa="دویدن", slug="running", sort_order=1)
    tennis = Sport.objects.create(name="Tennis", name_fa="تنیس", slug="tennis", sort_order=0)
    running.products.add(knee, hidden)
    tennis.products.add(elbow)
    return {"knee": knee, "elbow": elbow, "running": running, "tennis": tennis}


@pytest.mark.django_db
def test_sports_endpoint_lists_active_sports_in_order(catalog):
    Sport.objects.create(name="Hidden", slug="hidden", is_active=False)
    res = APIClient().get(reverse("products:sport-list"), {"lang": "fa"})
    assert res.status_code == status.HTTP_200_OK
    assert [s["slug"] for s in res.data] == ["tennis", "running"]
    running = res.data[1]
    assert running["name_localized"] == "دویدن"
    assert running["product_count"] == 1  # inactive products are not counted


@pytest.mark.django_db
def test_filter_products_by_sport(catalog):
    res = APIClient().get(reverse("products:product-list"), {"sport": "running"})
    assert [p["slug"] for p in res.data["results"]] == ["knee"]


@pytest.mark.django_db
def test_product_detail_includes_sports(catalog):
    res = APIClient().get(reverse("products:product-detail", kwargs={"slug": "knee"}))
    assert [s["slug"] for s in res.data["sports"]] == ["running"]


@pytest.mark.django_db
def test_admin_can_assign_sports(catalog):
    admin = User.objects.create_superuser(phone="09120001111", password="securepass123")
    client = APIClient()
    client.force_authenticate(admin)
    url = reverse("products:admin-product-detail", kwargs={"slug": "elbow"})
    res = client.patch(url, {"sports": [catalog["running"].id, catalog["tennis"].id]}, format="json")
    assert res.status_code == status.HTTP_200_OK, res.data
    assert set(catalog["elbow"].sports.values_list("slug", flat=True)) == {"running", "tennis"}


@pytest.mark.django_db
def test_seed_sports_links_products_by_injury_type(catalog, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    call_command("seed_sports", stdout=io.StringIO())
    football = Sport.objects.get(slug="football")
    assert catalog["knee"] in football.products.all()
    assert catalog["elbow"] not in football.products.all()
    assert football.image  # each sport gets its own cover photo
