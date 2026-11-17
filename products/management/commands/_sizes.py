"""Shared by the seed commands: give a demo product its sizes (not a command: leading underscore)."""
from products.models import ProductSize

STANDARD_SIZES = ["S", "M", "L", "XL"]


def set_demo_sizes(product, labels, total_stock):
    """Create the sizes once, splitting total_stock across them; then sync products.stock."""
    if not labels or ProductSize.objects.filter(product=product).exists():
        return
    share, extra = divmod(total_stock, len(labels))
    for i, label in enumerate(labels):
        ProductSize.objects.create(product=product, label=label, sort_order=i, stock=share + (1 if i < extra else 0))
    product.refresh_stock()
