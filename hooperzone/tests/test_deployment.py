import io

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from products.models import Category, Product


@pytest.fixture
def built_frontend(tmp_path, settings):
    (tmp_path / "index.html").write_text("<!doctype html><title>SPA</title><div id=root></div>", encoding="utf-8")
    settings.FRONTEND_DIST = tmp_path
    return tmp_path


def test_frontend_routes_serve_the_react_app(built_frontend):
    client = APIClient()
    for url in ["/", "/products/some-slug", "/cart"]:
        res = client.get(url)
        assert res.status_code == 200
        assert b"<title>SPA</title>" in res.content
        assert res["Cache-Control"] == "no-cache"


@pytest.mark.django_db
def test_api_routes_are_not_swallowed_by_the_frontend(built_frontend):
    client = APIClient()
    assert client.get("/api/").json()["message"] == "HooperZone API"
    assert client.get("/api/products/").status_code == 200
    assert client.get("/api/does-not-exist/").status_code == 404


def test_without_a_build_root_falls_back_to_api_index(tmp_path, settings):
    settings.FRONTEND_DIST = tmp_path  # no index.html
    assert APIClient().get("/").json()["message"] == "HooperZone API"


@pytest.mark.django_db
def test_seed_category_images_fills_only_missing_images(settings, tmp_path):
    from django.core.files.base import ContentFile

    settings.MEDIA_ROOT = tmp_path
    knee = Category.objects.create(name="Knee", slug="knee-braces")
    back = Category.objects.create(name="Back", slug="back-supports")
    back.image.save("uploaded.jpg", ContentFile(b"admin upload"), save=True)

    call_command("seed_category_images", stdout=io.StringIO())
    knee.refresh_from_db()
    back.refresh_from_db()
    assert knee.image.name.startswith("categories/knee-braces")
    assert back.image.name.startswith("categories/uploaded")  # admin upload kept


@pytest.mark.django_db
def test_seed_demo_store_skips_when_products_exist():
    cat = Category.objects.create(name="C", slug="c")
    Product.objects.create(category=cat, name="P", slug="p", description="d", price=1)
    out = io.StringIO()
    call_command("seed_demo_store", stdout=out)
    assert "skipping" in out.getvalue()
    assert Product.objects.count() == 1
