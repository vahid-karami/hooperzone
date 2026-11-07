"""Split size labels that hold several sizes ("M L", "M, L", "M/L") into one size per row.

0009 copied the old free-text size as one label, so a product typed as "M L" got a single
size "M L" instead of two. The existing row becomes the first size (carts and orders keep
pointing at it) and the others are created after it; the stock is split evenly because the
old text never said how much of each there was. Staff should check the per-size numbers.
"""
import re

from django.db import migrations
from django.db.models import F, Sum

SEPARATORS = re.compile(r"[\s,،/]+")


def split_labels(apps, schema_editor):
    Product = apps.get_model("products", "Product")
    ProductSize = apps.get_model("products", "ProductSize")
    for size in list(ProductSize.objects.all()):
        parts = [p for p in SEPARATORS.split(size.label.strip()) if p]
        if len(parts) < 2:
            continue
        taken = set(
            ProductSize.objects.filter(product_id=size.product_id).exclude(pk=size.pk).values_list("label", flat=True)
        )
        parts = [p for i, p in enumerate(parts) if p.lower() not in {t.lower() for t in taken} and p not in parts[:i]]
        if not parts:
            continue
        share, extra = divmod(size.stock, len(parts))
        later = ProductSize.objects.filter(product_id=size.product_id, sort_order__gt=size.sort_order)
        later.update(sort_order=F("sort_order") + len(parts) - 1)  # keep the sizes after it in order
        for i, label in enumerate(parts):
            fields = {"label": label[:20], "stock": share + (1 if i < extra else 0), "sort_order": size.sort_order + i}
            if i == 0:
                ProductSize.objects.filter(pk=size.pk).update(**fields)
            else:
                ProductSize.objects.create(product_id=size.product_id, sku="", is_active=size.is_active, **fields)
        total = ProductSize.objects.filter(product_id=size.product_id, is_active=True).aggregate(t=Sum("stock"))["t"]
        Product.objects.filter(pk=size.product_id).update(stock=total or 0)


class Migration(migrations.Migration):
    dependencies = [("products", "0011_merge_20261107_1005")]

    operations = [migrations.RunPython(split_labels, migrations.RunPython.noop)]
