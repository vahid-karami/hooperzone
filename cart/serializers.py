from rest_framework import serializers

from products.serializers import ProductListSerializer

from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    size = serializers.SerializerMethodField()
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = CartItem
        fields = ["id", "product", "product_id", "size", "quantity", "subtotal"]
        read_only_fields = ["id"]

    def get_size(self, obj):
        return {"id": obj.size_id, "label": obj.size.label, "stock": obj.size.stock} if obj.size_id else None


class CartSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    total_items = serializers.IntegerField(read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "items", "total_price", "total_items", "created_at", "updated_at"]

    def get_items(self, obj):
        items = obj.items.select_related("product", "size").prefetch_related("product__images")
        return CartItemSerializer(items, many=True).data
