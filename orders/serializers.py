from rest_framework import serializers

from hooperzone.fields import DigitsCharField

from .models import Order, OrderItem


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
        image = obj.product.images.order_by("-is_primary", "-created_at").first()
        return image.image.url if image else None


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

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
            "subtotal",
            "shipping_cost",
            "discount",
            "total",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "order_number", "created_at", "updated_at"]


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
    shipping_country = serializers.CharField(max_length=100, required=False, default="US")
    shipping_phone = DigitsCharField(max_length=15)
    notes = serializers.CharField(required=False, allow_blank=True)
