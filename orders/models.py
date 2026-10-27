from django.conf import settings
from django.db import models
from django.db.models import F


class ShopSettings(models.Model):
    """Store-wide settings edited in the admin portal. Always a single row (pk=1)."""

    shipping_post = models.PositiveIntegerField(default=60000, help_text="Post (sefareshi) fee, Toman")
    shipping_pishtaz = models.PositiveIntegerField(default=90000, help_text="Post Pishtaz fee, Toman")
    shipping_tipax = models.PositiveIntegerField(default=150000, help_text="Tipax fee, Toman")
    unpaid_order_timeout_minutes = models.PositiveIntegerField(
        default=60, help_text="Unpaid orders older than this are cancelled and their stock released. 0 = never."
    )
    low_stock_threshold = models.PositiveIntegerField(default=5)

    store_phone = models.CharField(max_length=30, blank=True)
    store_email = models.EmailField(blank=True)
    store_address = models.TextField(blank=True)
    instagram = models.CharField(max_length=100, blank=True, help_text="Instagram username without @")
    telegram = models.CharField(max_length=100, blank=True, help_text="Telegram username without @")
    whatsapp = models.CharField(max_length=30, blank=True)
    working_hours = models.CharField(max_length=200, blank=True)
    enamad_html = models.TextField(blank=True, help_text="Badge code from enamad.ir")
    samandehi_html = models.TextField(blank=True, help_text="Badge code from samandehi.ir")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "shop_settings"
        verbose_name = "Shop settings"
        verbose_name_plural = "Shop settings"

    def __str__(self):
        return "Shop settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def shipping_fee(self, method):
        return {
            Order.SHIPPING_POST: self.shipping_post,
            Order.SHIPPING_PISHTAZ: self.shipping_pishtaz,
            Order.SHIPPING_TIPAX: self.shipping_tipax,
        }[method]

    def shipping_methods(self):
        labels = {
            Order.SHIPPING_POST: ("پست سفارشی", "Post (registered)", "3-7"),
            Order.SHIPPING_PISHTAZ: ("پست پیشتاز", "Post Pishtaz (express)", "2-4"),
            Order.SHIPPING_TIPAX: ("تیپاکس", "Tipax", "1-3"),
        }
        return [
            {"code": code, "label_fa": fa, "label_en": en, "days": days, "fee": self.shipping_fee(code)}
            for code, (fa, en, days) in labels.items()
        ]


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_PROCESSING = "processing"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_PROCESSING, "Processing"),
        (STATUS_SHIPPED, "Shipped"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    PAYMENT_STATUS_PENDING = "pending"
    PAYMENT_STATUS_PAID = "paid"
    PAYMENT_STATUS_FAILED = "failed"
    PAYMENT_STATUS_REFUNDED = "refunded"

    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_PENDING, "Pending"),
        (PAYMENT_STATUS_PAID, "Paid"),
        (PAYMENT_STATUS_FAILED, "Failed"),
        (PAYMENT_STATUS_REFUNDED, "Refunded"),
    ]

    SHIPPING_POST = "post"
    SHIPPING_PISHTAZ = "pishtaz"
    SHIPPING_TIPAX = "tipax"

    SHIPPING_CHOICES = [
        (SHIPPING_POST, "Post"),
        (SHIPPING_PISHTAZ, "Post Pishtaz"),
        (SHIPPING_TIPAX, "Tipax"),
    ]

    # Staff may only move an order forward along this path (or cancel it).
    STATUS_FLOW = [STATUS_PENDING, STATUS_CONFIRMED, STATUS_PROCESSING, STATUS_SHIPPED, STATUS_DELIVERED]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    order_number = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default=PAYMENT_STATUS_PENDING
    )

    shipping_address = models.TextField()
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100, blank=True)
    shipping_zip = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=100, default="IR")
    shipping_phone = models.CharField(max_length=15)
    shipping_method = models.CharField(max_length=20, choices=SHIPPING_CHOICES, default=SHIPPING_POST)
    tracking_code = models.CharField(max_length=100, blank=True)

    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    payment_gateway = models.CharField(max_length=20, blank=True)
    payment_authority = models.CharField(max_length=100, blank=True)
    payment_ref_id = models.CharField(max_length=100, blank=True)
    payment_card_pan = models.CharField(max_length=30, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "orders"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "payment_status", "created_at"])]

    def __str__(self):
        return f"Order {self.order_number}"

    def cancel(self, restock=True):
        """Cancel the order and put its items back in stock. Call inside a transaction."""
        from products.models import Product

        if self.status == self.STATUS_CANCELLED:
            return
        self.status = self.STATUS_CANCELLED
        self.save(update_fields=["status", "updated_at"])
        if restock:
            for item in self.items.all():
                if item.product_id:
                    Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.quantity)

    def can_move_to(self, new_status):
        if self.status == self.STATUS_CANCELLED:
            return new_status == self.STATUS_CANCELLED
        if new_status == self.STATUS_CANCELLED:
            return self.status != self.STATUS_DELIVERED
        return self.STATUS_FLOW.index(new_status) >= self.STATUS_FLOW.index(self.status)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    class Meta:
        db_table = "order_items"

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"

    @property
    def subtotal(self):
        return self.product_price * self.quantity
