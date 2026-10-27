from rest_framework import serializers

from hooperzone.fields import DigitsCharField

from .models import Order, OrderItem, ShopSettings


class OrderItemSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True, default=None)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_slug", "product_image", "product_name", "product_price", "quantity", "subtotal"]
        read_only_fields = ["id"]

    def get_product_image(self, obj):
        if not obj.product_id:
            return None
        # Sorted in Python so a prefetch of items__product__images is used.
        images = sorted(obj.product.images.all(), key=lambda i: (not i.is_primary, -i.created_at.timestamp()))
        return images[0].image.url if images else None


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    shipping_method_display = serializers.CharField(source="get_shipping_method_display", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "status_display",
            "payment_status",
            "items",
            "shipping_address",
            "shipping_city",
            "shipping_state",
            "shipping_zip",
            "shipping_country",
            "shipping_phone",
            "shipping_method",
            "shipping_method_display",
            "tracking_code",
            "payment_ref_id",
            "paid_at",
            "subtotal",
            "shipping_cost",
            "discount",
            "total",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "order_number", "created_at", "updated_at"]


class ShopInfoSerializer(serializers.ModelSerializer):
    shipping_methods = serializers.SerializerMethodField()

    class Meta:
        model = ShopSettings
        fields = [
            "store_phone", "store_email", "store_address", "instagram", "telegram", "whatsapp",
            "working_hours", "enamad_html", "samandehi_html", "shipping_methods",
        ]

    def get_shipping_methods(self, obj):
        return obj.shipping_methods()


class ShopSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopSettings
        exclude = ["id"]
        read_only_fields = ["updated_at"]


class AdminOrderSerializer(OrderSerializer):
    """Order as staff see it: includes the customer."""

    customer = serializers.SerializerMethodField()

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ["customer"]

    def get_customer(self, obj):
        user = obj.user
        return {
            "id": user.id,
            "name": user.get_full_name() or user.username or user.phone,
            "phone": user.phone,
            "email": user.email,
        }


class OrderCreateSerializer(serializers.Serializer):
    shipping_address = serializers.CharField()
    shipping_city = serializers.CharField(max_length=100)
    shipping_state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    shipping_zip = DigitsCharField(max_length=20)
    shipping_country = serializers.CharField(max_length=100, required=False, default="IR")
    shipping_phone = DigitsCharField(max_length=15)
    shipping_method = serializers.ChoiceField(choices=Order.SHIPPING_CHOICES, required=False, default=Order.SHIPPING_POST)
    notes = serializers.CharField(required=False, allow_blank=True)
