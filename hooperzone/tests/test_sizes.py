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
