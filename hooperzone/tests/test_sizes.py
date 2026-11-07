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


# --- Orders -------------------------------------------------------------------------------

ADDRESS = {
    "shipping_address": "Tehran, Azadi St", "shipping_city": "Tehran", "shipping_zip": "1234567890",
    "shipping_phone": "09121234567",
}


def checkout(client):
    from django.urls import reverse

    return client.post(reverse("orders:order-create"), ADDRESS, format="json")


def test_checkout_takes_stock_from_the_chosen_size(sized, shopper):
    add(shopper, sized["product"], sized["M"], 2)
    res = checkout(shopper)
    assert res.status_code == 201, res.data
    assert res.data["items"][0]["size_label"] == "M"
    sized["M"].refresh_from_db()
    sized["S"].refresh_from_db()
    assert (sized["S"].stock, sized["M"].stock) == (2, 3)
    assert stock_of(sized["product"]) == 5


def test_cancelling_puts_stock_back_on_the_size(sized, shopper):
    from django.urls import reverse

    add(shopper, sized["product"], sized["S"], 2)
    number = checkout(shopper).data["order_number"]
    assert shopper.post(reverse("orders:order-cancel", kwargs={"order_number": number})).status_code == 200
    sized["S"].refresh_from_db()
    assert sized["S"].stock == 2 and stock_of(sized["product"]) == 7


def test_checkout_refuses_more_than_the_size_has(sized, shopper):
    from cart.models import CartItem

    add(shopper, sized["product"], sized["S"], 2)
    CartItem.objects.update(quantity=3)  # e.g. stock dropped after it was added
    assert checkout(shopper).status_code == 400


def test_checkout_asks_for_a_size_on_an_old_size_less_line(sized, shopper):
    from cart.models import Cart, CartItem

    cart = Cart.objects.create(user=shopper.handler._force_user)
    CartItem.objects.create(cart=cart, product=sized["product"], quantity=1)
    res = checkout(shopper)
    assert res.status_code == 400 and "size" in res.data["error"].lower()


def test_order_keeps_the_size_label_after_the_size_is_deleted(sized, shopper):
    from orders.models import OrderItem

    add(shopper, sized["product"], sized["M"])
    checkout(shopper)
    sized["M"].delete()
    item = OrderItem.objects.get()
    assert item.size is None and item.size_label == "M"


# --- Shop API -----------------------------------------------------------------------------


def test_product_page_lists_active_sizes_and_the_size_guide(sized, client):
    from django.urls import reverse

    guide = SizeGuide.objects.create(name="Knee", title_fa="راهنمای سایز زانوبند", columns=COLUMNS, rows=ROWS)
    sized["product"].size_guide = guide
    sized["product"].save()
    ProductSize.objects.create(product=sized["product"], label="XL", stock=4, is_active=False, sort_order=9)

    data = client.get(reverse("products:product-detail", kwargs={"slug": "sleeve"})).data
    assert [s["label"] for s in data["sizes"]] == ["S", "M"]
    assert data["sizes"][0] == {"id": sized["S"].id, "label": "S", "stock": 2, "in_stock": True}
    assert data["size_guide"]["title_fa"] == "راهنمای سایز زانوبند"
    assert data["size_guide"]["rows"] == ROWS
    assert data["stock"] == 7


def test_product_list_shows_size_labels_without_extra_queries(sized, client, django_assert_max_num_queries):
    from django.urls import reverse

    for i in range(5):
        cat = sized["product"].category
        p = Product.objects.create(category=cat, name=f"P{i}", slug=f"p{i}", description="d", price=1)
        ProductSize.objects.create(product=p, label="M", stock=1)
    with django_assert_max_num_queries(6):
        res = client.get(reverse("products:product-list"))
    labels = {p["slug"]: p["size_labels"] for p in res.data["results"]}
    assert labels["sleeve"] == ["S", "M"] and labels["p0"] == ["M"]


def test_product_list_filters_by_size(sized, client):
    from django.urls import reverse

    Product.objects.create(category=sized["product"].category, name="Plain", slug="plain", description="d", price=1)
    res = client.get(reverse("products:product-list"), {"size": "m"})
    assert [p["slug"] for p in res.data["results"]] == ["sleeve"]


# --- Admin API ----------------------------------------------------------------------------


@pytest.fixture
def owner(db):
    from django.contrib.auth import get_user_model
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(get_user_model().objects.create_superuser(phone="09120009999", password="securepass123"))
    return client


def admin_url(slug=None):
    from django.urls import reverse

    if slug:
        return reverse("products:admin-product-detail", kwargs={"slug": slug})
    return reverse("products:admin-product-list")


def test_admin_creates_a_product_with_sizes(product, owner):
    res = owner.post(admin_url(), {
        "name": "Ankle", "description": "d", "price": 50, "stock": 99, "category": product.category_id,
        "sizes": [{"label": "S", "stock": 3}, {"label": "M", "stock": 4, "sku": "HZ-A-M"}],
    }, format="json")
    assert res.status_code == 201, res.data
    assert [(s["label"], s["stock"], s["sort_order"]) for s in res.data["sizes"]] == [("S", 3, 0), ("M", 4, 1)]
    assert res.data["stock"] == 7  # the sizes' total, not the 99 that was typed


def test_admin_updates_renames_swaps_and_removes_sizes(sized, owner):
    s, m = sized["S"], sized["M"]
    res = owner.patch(admin_url("sleeve"), {"sizes": [
        {"id": s.id, "label": "M", "stock": 2},  # swap S <-> M
        {"id": m.id, "label": "S", "stock": 6},
        {"label": "XL", "stock": 1},
    ]}, format="json")
    assert res.status_code == 200, res.data
    assert [(x["id"], x["label"]) for x in res.data["sizes"][:2]] == [(s.id, "M"), (m.id, "S")]
    assert res.data["stock"] == 9

    res = owner.patch(admin_url("sleeve"), {"sizes": [{"id": s.id, "label": "M", "stock": 2}]}, format="json")
    assert [x["label"] for x in res.data["sizes"]] == ["M"] and res.data["stock"] == 2


def test_admin_can_go_back_to_no_sizes(sized, owner):
    res = owner.patch(admin_url("sleeve"), {"sizes": [], "stock": 11}, format="json")
    assert res.data["sizes"] == [] and res.data["stock"] == 11


def test_admin_leaves_sizes_alone_when_not_sent(sized, owner):
    res = owner.patch(admin_url("sleeve"), {"price": 120}, format="json")
    assert len(res.data["sizes"]) == 2 and res.data["stock"] == 7


@pytest.mark.parametrize("sizes", [
    [{"label": "M"}, {"label": "m"}],  # duplicate label
    [{"label": " "}],  # empty label
    [{"label": "S", "sku": "X1"}, {"label": "M", "sku": "X1"}],  # duplicate SKU
    [{"label": "S", "stock": -1}],  # negative stock
    [{"label": f"S{i}"} for i in range(31)],  # too many
])
def test_admin_rejects_invalid_sizes(sized, owner, sizes):
    assert owner.patch(admin_url("sleeve"), {"sizes": sizes}, format="json").status_code == 400
    assert ProductSize.objects.filter(product=sized["product"]).count() == 2  # nothing half-saved


def test_admin_rejects_a_size_id_from_another_product(sized, owner):
    other = Product.objects.create(category=sized["product"].category, name="B", slug="b", description="d", price=1)
    foreign = ProductSize.objects.create(product=other, label="L")
    res = owner.patch(admin_url("sleeve"), {"sizes": [{"id": foreign.id, "label": "L"}]}, format="json")
    assert res.status_code == 400


def test_admin_rejects_a_sku_used_by_another_product(sized, owner):
    other = Product.objects.create(category=sized["product"].category, name="B", slug="b", description="d", price=1)
    ProductSize.objects.create(product=other, label="L", sku="TAKEN")
    res = owner.patch(admin_url("sleeve"), {"sizes": [{"label": "L", "sku": "TAKEN"}]}, format="json")
    assert res.status_code == 400


def test_size_guide_crud_and_assignment(sized, owner):
    from django.urls import reverse

    url = reverse("products:admin-size-guide-list")
    res = owner.post(url, {"name": "Knee", "title_fa": "راهنما", "columns": COLUMNS, "rows": ROWS}, format="json")
    assert res.status_code == 201, res.data
    guide_id = res.data["id"]
    assert owner.post(url, {"name": "Bad", "columns": COLUMNS, "rows": [{"size": "S", "values": ["1"]}]},
                      format="json").status_code == 400

    res = owner.patch(admin_url("sleeve"), {"size_guide": guide_id}, format="json")
    assert res.data["size_guide"] == guide_id and res.data["size_guide_name"] == "Knee"
    assert owner.get(url).data[0]["product_count"] == 1


def test_size_guide_accepts_the_table_as_json_text_in_a_multipart_form(owner, db):
    import json

    from django.urls import reverse

    res = owner.post(reverse("products:admin-size-guide-list"), {
        "name": "Wrist", "columns": json.dumps(COLUMNS), "rows": json.dumps(ROWS),
    }, format="multipart")
    assert res.status_code == 201, res.data
    assert res.data["rows"] == ROWS


def test_product_editor_manages_sizes_and_guides_but_cannot_delete_guides(sized, db):
    import io

    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group
    from django.core.management import call_command
    from django.urls import reverse
    from rest_framework.test import APIClient

    call_command("setup_roles", stdout=io.StringIO())
    user = get_user_model().objects.create_user(phone="09125556666", password="securepass123", is_staff=True)
    user.groups.add(Group.objects.get(name="Product editors"))
    client = APIClient()
    client.force_authenticate(get_user_model().objects.get(pk=user.pk))

    res = client.patch(admin_url("sleeve"), {"sizes": [{"id": sized["S"].id, "label": "S", "stock": 8}]}, format="json")
    assert res.status_code == 200 and res.data["stock"] == 8
    res = client.post(reverse("products:admin-size-guide-list"), {"name": "K", "columns": COLUMNS, "rows": ROWS},
                      format="json")
    assert res.status_code == 201
    detail = reverse("products:admin-size-guide-detail", kwargs={"pk": res.data["id"]})
    assert client.delete(detail).status_code == 403


# --- Seeds --------------------------------------------------------------------------------


def test_seed_size_guides_is_idempotent_and_never_overwrites(db):
    import io

    from django.core.management import call_command

    call_command("seed_size_guides", stdout=io.StringIO())
    knee = SizeGuide.objects.get(name="Knee supports")
    knee.title_fa = "ویرایش شده"
    knee.save()
    out = io.StringIO()
    call_command("seed_size_guides", stdout=out)
    assert "0 created" in out.getvalue()
    assert SizeGuide.objects.get(name="Knee supports").title_fa == "ویرایش شده"


def test_demo_store_gets_sizes_and_size_guides(db, settings, tmp_path):
    import io

    from django.core.management import call_command

    settings.MEDIA_ROOT = tmp_path
    call_command("seed_demo_store", stdout=io.StringIO())
    knee = Product.objects.get(slug="premium-knee-brace")
    assert [s.label for s in knee.sizes.all()] == ["S", "M", "L", "XL"]
    assert knee.stock == sum(s.stock for s in knee.sizes.all()) == 50
    assert knee.size_guide.name == "Knee supports"
    one_size = Product.objects.filter(sizes__isnull=True)
    assert one_size.exists() and not one_size.filter(size_guide__isnull=False).exists()


def test_admin_typed_stock_cannot_override_the_sizes_total(sized, owner):
    res = owner.patch(admin_url("sleeve"), {"stock": 500}, format="json")
    assert res.status_code == 200 and res.data["stock"] == 7


def test_size_guide_diagram_can_be_uploaded_and_removed(owner, settings, tmp_path, db):
    import io
    import json

    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.urls import reverse
    from PIL import Image

    settings.MEDIA_ROOT = tmp_path
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "navy").save(buf, "PNG")
    res = owner.post(reverse("products:admin-size-guide-list"), {
        "name": "Diagram", "columns": json.dumps(COLUMNS), "rows": json.dumps(ROWS),
        "image": SimpleUploadedFile("d.png", buf.getvalue(), content_type="image/png"),
    }, format="multipart")
    assert res.status_code == 201 and res.data["image"]
    guide = SizeGuide.objects.get(pk=res.data["id"])
    path = guide.image.path
    detail = reverse("products:admin-size-guide-detail", kwargs={"pk": guide.pk})
    table = {"columns": json.dumps(COLUMNS), "rows": json.dumps(ROWS)}
    res = owner.patch(detail, {"image": "", **table}, format="multipart")
    assert res.status_code == 200, res.data
    assert res.data["image"] is None
    import os

    assert not os.path.exists(path)


# --- Migration 0012: split "M L" labels --------------------------------------------------


def test_migration_splits_a_label_holding_several_sizes(transactional_db):
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    before, after = [("products", "0011_merge_20261107_1005")], [("products", "0012_split_multi_size_labels")]
    executor = MigrationExecutor(connection)
    executor.migrate(before)
    old = executor.loader.project_state(before).apps
    cat = old.get_model("products", "Category").objects.create(name="Ankle", slug="ankle")
    product = old.get_model("products", "Product").objects.create(
        category=cat, name="Stabilizer", slug="stab", description="d", price=1, stock=5
    )
    Size = old.get_model("products", "ProductSize")
    both = Size.objects.create(product=product, label="M L", stock=5, sort_order=0)
    Size.objects.create(product=product, label="XL", stock=2, sort_order=1)
    other = old.get_model("products", "Product").objects.create(
        category=cat, name="Other", slug="other", description="d", price=1
    )
    Size.objects.create(product=other, label="39-41", stock=3)  # a range is one size: left alone

    executor = MigrationExecutor(connection)
    executor.migrate(after)
    new = executor.loader.project_state(after).apps
    sizes = new.get_model("products", "ProductSize").objects.filter(product_id=product.pk).order_by("sort_order")
    assert [(s.label, s.stock) for s in sizes] == [("M", 3), ("L", 2), ("XL", 2)]
    assert sizes[0].pk == both.pk  # carts and orders keep pointing at the first part
    assert new.get_model("products", "Product").objects.get(pk=product.pk).stock == 7
    others = new.get_model("products", "ProductSize").objects.filter(product_id=other.pk)
    assert list(others.values_list("label", flat=True)) == ["39-41"]
    MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())


def test_database_rejects_a_label_with_several_sizes(product):
    for label in ("M L", "M,L", "M،L", "M/L"):
        with pytest.raises(IntegrityError), transaction.atomic():
            ProductSize.objects.create(product=product, label=label)
    ProductSize.objects.create(product=product, label="39-41")  # a range is fine


def test_admin_asks_to_add_each_size_separately(sized, owner):
    res = owner.patch(admin_url("sleeve"), {"sizes": [{"label": "M L", "stock": 4}]}, format="json")
    assert res.status_code == 400
    assert "separately" in str(res.data["sizes"])
    assert ProductSize.objects.filter(product=sized["product"]).count() == 2
