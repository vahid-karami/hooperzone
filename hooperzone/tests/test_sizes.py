"""Product sizes and size guides: database rules, stock sync, and the APIs that use them."""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from products.models import Category, Product, ProductSize, SizeGuide, validate_size_guide_table

COLUMNS = [{"label_fa": "دور ران", "label_en": "Thigh", "unit": "cm"}, {"label_fa": "دور ساق", "unit": "cm"}]
ROWS = [{"size": "S", "values": ["38-41", "28-31"]}, {"size": "M", "values": ["41-44", "31-34"]}]


@pytest.fixture
def product(db):
    cat = Category.objects.create(name="Knee", slug="knee")
    return Product.objects.create(category=cat, name="Sleeve", slug="sleeve", description="d", price=100, stock=0)


def stock_of(product):
    return Product.objects.get(pk=product.pk).stock


def test_size_label_is_unique_per_product_ignoring_case(product):
    ProductSize.objects.create(product=product, label="M")
    with pytest.raises(IntegrityError), transaction.atomic():
        ProductSize.objects.create(product=product, label="m")


def test_same_label_on_two_products_is_fine(product):
    other = Product.objects.create(category=product.category, name="B", slug="b", description="d", price=1)
    ProductSize.objects.create(product=product, label="M")
    ProductSize.objects.create(product=other, label="M")


def test_sku_is_unique_but_blank_skus_may_repeat(product):
    ProductSize.objects.create(product=product, label="S")
    ProductSize.objects.create(product=product, label="M")  # both blank SKUs
    ProductSize.objects.create(product=product, label="L", sku="HZ-1-L")
    with pytest.raises(IntegrityError), transaction.atomic():
        ProductSize.objects.create(product=product, label="XL", sku="HZ-1-L")


def test_empty_label_is_rejected_by_the_database(product):
    with pytest.raises(IntegrityError), transaction.atomic():
        ProductSize.objects.create(product=product, label="")


def test_product_stock_follows_its_active_sizes(product):
    s = ProductSize.objects.create(product=product, label="S", stock=3)
    ProductSize.objects.create(product=product, label="M", stock=4)
    assert stock_of(product) == 7
    ProductSize.objects.create(product=product, label="L", stock=9, is_active=False)
    assert stock_of(product) == 7  # inactive sizes can't be bought
    s.stock = 1
    s.save()
    assert stock_of(product) == 5
    ProductSize.objects.filter(product=product).delete()
    assert stock_of(product) == 0


def test_product_without_sizes_keeps_its_own_stock(product):
    Product.objects.filter(pk=product.pk).update(stock=12)
    product.refresh_stock()
    assert stock_of(product) == 12


def test_deleting_a_size_guide_keeps_the_products(product):
    guide = SizeGuide.objects.create(name="Knee", columns=COLUMNS, rows=ROWS)
    product.size_guide = guide
    product.save()
    guide.delete()
    product.refresh_from_db()
    assert product.size_guide is None


def test_size_guide_table_validation():
    validate_size_guide_table(COLUMNS, ROWS)
    bad = [
        ([], ROWS),  # no columns
        ([{"unit": "cm"}], [{"size": "S", "values": ["1"]}]),  # column without a name
        ([{"label_fa": "x", "colour": "red"}], [{"size": "S", "values": ["1"]}]),  # unknown key
        (COLUMNS, []),  # no rows
        (COLUMNS, [{"size": "S", "values": ["1"]}]),  # wrong number of values
        (COLUMNS, [{"size": "", "values": ["1", "2"]}]),  # no size name
        (COLUMNS, [{"size": "S", "values": ["1", "2"]}, {"size": "s", "values": ["1", "2"]}]),  # duplicate
        (COLUMNS, [{"size": "S", "values": ["x" * 41, "2"]}]),  # value too long
    ]
    for columns, rows in bad:
        with pytest.raises(ValidationError):
            validate_size_guide_table(columns, rows)


# --- Cart ---------------------------------------------------------------------------------


@pytest.fixture
def sized(product):
    small = ProductSize.objects.create(product=product, label="S", stock=2, sort_order=0)
    medium = ProductSize.objects.create(product=product, label="M", stock=5, sort_order=1)
    return {"product": product, "S": small, "M": medium}


@pytest.fixture
def shopper(db):
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient

    user = get_user_model().objects.create_user(phone="09123334444", password="securepass123")
    client = APIClient()
    client.force_authenticate(user)
    return client


def add(client, product, size=None, quantity=1):
    from django.urls import reverse

    data = {"product_id": product.id, "quantity": quantity}
    if size is not None:
        data["size_id"] = size.id
    return client.post(reverse("cart:cart-add"), data, format="json")


def test_cart_needs_a_size_for_a_sized_product(sized, shopper):
    res = add(shopper, sized["product"])
    assert res.status_code == 400 and "size" in res.data["error"].lower()


def test_cart_rejects_a_size_of_another_product(sized, shopper):
    other = Product.objects.create(category=sized["product"].category, name="B", slug="b", description="d", price=1)
    foreign = ProductSize.objects.create(product=other, label="S", stock=9)
    assert add(shopper, sized["product"], foreign).status_code == 400


def test_cart_rejects_an_inactive_size(sized, shopper):
    sized["M"].is_active = False
    sized["M"].save()
    assert add(shopper, sized["product"], sized["M"]).status_code == 400


def test_cart_keeps_one_line_per_size_and_checks_that_sizes_stock(sized, shopper):
    assert add(shopper, sized["product"], sized["S"], 2).status_code == 200
    assert add(shopper, sized["product"], sized["S"]).status_code == 400  # only 2 small ones
    res = add(shopper, sized["product"], sized["M"], 3)
    assert res.status_code == 200
    lines = {item["size"]["label"]: item["quantity"] for item in res.data["items"]}
    assert lines == {"S": 2, "M": 3}


def test_cart_update_checks_the_sizes_stock(sized, shopper):
    from django.urls import reverse

    item_id = add(shopper, sized["product"], sized["S"]).data["items"][0]["id"]
    res = shopper.patch(reverse("cart:cart-update"), {"item_id": item_id, "quantity": 3}, format="json")
    assert res.status_code == 400


def test_size_less_product_takes_no_size(product, shopper):
    Product.objects.filter(pk=product.pk).update(stock=4)
    assert add(shopper, product).status_code == 200
    other_size = ProductSize.objects.create(
        product=Product.objects.create(category=product.category, name="C", slug="c", description="d", price=1),
        label="S",
    )
    assert add(shopper, product, other_size).status_code == 400


def test_database_allows_one_size_less_line_per_product(product, shopper):
    from cart.models import Cart, CartItem

    cart = Cart.objects.create(user=shopper.handler._force_user)
    CartItem.objects.create(cart=cart, product=product)
    with pytest.raises(IntegrityError), transaction.atomic():
        CartItem.objects.create(cart=cart, product=product)
