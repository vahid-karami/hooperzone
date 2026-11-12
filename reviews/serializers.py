from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Review


class ReviewAuthorSerializer(serializers.ModelSerializer):
    """Public view of a reviewer: never expose phone, email or address."""

    display_name = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ["id", "first_name", "display_name"]

    def get_display_name(self, obj):
        if obj.first_name:
            return f"{obj.first_name} {obj.last_name[:1]}".strip()
        return "Customer"


class ReviewSerializer(serializers.ModelSerializer):
    user = ReviewAuthorSerializer(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "rating",
            "title",
            "comment",
            "is_verified_purchase",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_verified_purchase", "created_at", "updated_at"]


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["rating", "title", "comment"]

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
