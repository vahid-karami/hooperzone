from rest_framework import serializers

from products.serializers import ProductListSerializer

from .models import FavoriteItem, FavoriteList


class FavoriteItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = FavoriteItem
        fields = ["id", "product", "product_id", "created_at"]
        read_only_fields = ["id", "created_at"]


class FavoriteListSerializer(serializers.ModelSerializer):
    items = FavoriteItemSerializer(many=True, read_only=True)
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = FavoriteList
        fields = ["id", "items", "total_items", "created_at", "updated_at"]

    def get_total_items(self, obj):
        return obj.items.count()
