from django.conf import settings
from django.db import models
from django.db.models import Q


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "carts"

    def __str__(self):
        return f"Cart for {self.user.phone}"

    @property
    def total_price(self):
        return sum(item.subtotal for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    # Required when the product has sizes; a removed size removes the cart line.
    size = models.ForeignKey("products.ProductSize", on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cart_items"
        constraints = [
            models.UniqueConstraint(fields=["cart", "product", "size"], name="unique_cart_product_size"),
            # NULLs never collide in a unique index, so size-less lines need their own rule.
            models.UniqueConstraint(
                fields=["cart", "product"], condition=Q(size__isnull=True), name="unique_cart_product_without_size"
            ),
        ]

    def __str__(self):
        size = f" ({self.size.label})" if self.size_id else ""
        return f"{self.quantity}x {self.product.name}{size}"

    @property
    def available_stock(self):
        return self.size.stock if self.size_id else self.product.stock

    @property
    def subtotal(self):
        return self.product.effective_price * self.quantity
