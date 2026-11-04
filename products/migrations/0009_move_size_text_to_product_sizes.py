"""Turn the old free-text products.size into product_sizes rows.

A real size ("M", "L") becomes one ProductSize holding the product's whole stock. "One size"
values stay size-less: those products are sold without choosing a size.
"""
from django.db import migrations

ONE_SIZE = {"", "one size", "onesize", "free size", "standard", "یک سایز", "یک اندازه", "استاندارد", "فری سایز"}


def forwards(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    ProductSize = apps.get_model("products", "ProductSize")
    for product in Product.objects.exclude(size=""):
        label = product.size.strip()[:20]
        if label.lower() in ONE_SIZE:
            continue
        ProductSize.objects.get_or_create(product=product, label=label, defaults={"stock": product.stock})


def backwards(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    ProductSize = apps.get_model("products", "ProductSize")
    for product in Product.objects.all():
        first = ProductSize.objects.filter(product=product).order_by("sort_order", "id").first()
        if first:
            Product.objects.filter(pk=product.pk).update(size=first.label)


class Migration(migrations.Migration):
    dependencies = [("products", "0008_size_guides_and_product_sizes")]

    operations = [migrations.RunPython(forwards, backwards)]
