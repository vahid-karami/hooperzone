from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["user", "product", "rating", "title", "is_verified_purchase", "created_at"]
    list_filter = ["rating", "is_verified_purchase"]
    search_fields = ["user__phone", "product__name", "title"]
    readonly_fields = ["created_at", "updated_at"]
