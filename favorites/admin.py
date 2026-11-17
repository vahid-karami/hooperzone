from django.contrib import admin

from .models import FavoriteItem, FavoriteList


class FavoriteItemInline(admin.TabularInline):
    model = FavoriteItem
    extra = 0
    raw_id_fields = ["product"]


@admin.register(FavoriteList)
class FavoriteListAdmin(admin.ModelAdmin):
    list_display = ["user", "item_count", "updated_at"]
    inlines = [FavoriteItemInline]

    def item_count(self, obj):
        return obj.items.count()
