import json
import re

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from products.models import Category, Product
from reviews.models import Review

INDEX = """<!doctype html><html><head>
<meta name="description" content="default" />
<meta name="robots" content="index, follow" />
<title>SPA</title></head><body><div id=root></div></body></html>"""


@pytest.fixture
def site(db, tmp_path, settings):
    (tmp_path / "index.html").write_text(INDEX, encoding="utf-8")
    settings.FRONTEND_DIST = tmp_path
    settings.SITE_URL = "https://hooperzone.ir"
    cat = Category.objects.create(name="Knee", name_fa="زانوبند", slug="knee", description_fa="زانوبندهای ورزشی")
    product = Product.objects.create(
        category=cat, name="Pro Brace", name_fa="زانوبند حرفه‌ای", slug="pro-brace", brand="HZ",
        description="d", description_fa="زانوبند </script> حرفه‌ای برای فوتبال", price=1_000_000, stock=3,
    )
    Product.objects.create(category=cat, name="Hidden", slug="hidden", description="d", price=1, is_active=False)
    user = get_user_model().objects.create_user(phone="09121112222", password="securepass123")
    Review.objects.create(user=user, product=product, rating=4, title="t", comment="c")
    return product


def ld_blocks(html):
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]


def test_product_page_has_its_own_meta_and_json_ld(site):
    res = APIClient().get("/products/pro-brace")
    html = res.content.decode()
    assert res.status_code == 200
    assert "<title>زانوبند حرفه‌ای | هوپرزون</title>" in html
    assert '<link rel="canonical" href="https://hooperzone.ir/products/pro-brace" />' in html
    assert 'property="og:type" content="product"' in html
    blocks = ld_blocks(html)
    product = next(b for b in blocks if b["@type"] == "Product")
    assert product["offers"]["price"] == "10000000"  # Toman stored, Rials published
    assert product["offers"]["priceCurrency"] == "IRR"
    assert product["aggregateRating"]["reviewCount"] == 1
    assert product["brand"]["name"] == "HZ"
    assert any(b["@type"] == "BreadcrumbList" for b in blocks)
    # User text can't break out of the JSON-LD script.
    assert "زانوبند </script>" not in html


def test_custom_meta_title_wins(site):
    site.meta_title = "خرید زانوبند حرفه‌ای"
    site.save()
    assert "<title>خرید زانوبند حرفه‌ای | هوپرزون</title>" in APIClient().get("/products/pro-brace").content.decode()


@pytest.mark.parametrize("url", ["/products/hidden", "/products/nope", "/no-such-page", "/products?category=nope"])
def test_unknown_pages_are_404_and_noindex(site, url):
    res = APIClient().get(url)
    assert res.status_code == 404
    assert 'content="noindex, nofollow"' in res.content.decode()


def test_private_pages_are_noindex(site):
    for url in ["/cart", "/checkout", "/admin-portal/orders", "/orders/ORD-1"]:
        res = APIClient().get(url)
        assert res.status_code == 200
        assert 'content="noindex, nofollow"' in res.content.decode(), url


def test_home_has_organization_and_search(site):
    types = {b["@type"] for b in ld_blocks(APIClient().get("/").content.decode())}
    assert {"OnlineStore", "WebSite"} <= types


def test_category_listing_meta(site):
    html = APIClient().get("/products?category=knee").content.decode()
    assert "<title>خرید زانوبند | هوپرزون</title>" in html
    assert 'href="https://hooperzone.ir/products?category=knee"' in html


def test_robots_txt(site):
    body = APIClient().get("/robots.txt").content.decode()
    assert "Disallow: /admin-portal" in body
    assert "Sitemap: https://hooperzone.ir/sitemap.xml" in body


def test_sitemap_lists_active_products_with_images(site, settings, tmp_path):
    from products.models import ProductImage

    settings.MEDIA_ROOT = tmp_path
    ProductImage.objects.create(product=site, image="products/p.jpg")
    body = APIClient().get("/sitemap.xml").content.decode()
    assert "<loc>https://hooperzone.ir/products/pro-brace</loc>" in body
    assert "/products/hidden" not in body
    assert "<image:loc>https://hooperzone.ir/media/products/p.jpg</image:loc>" in body
    assert "https://hooperzone.ir/terms" in body
