from django.contrib import admin

from .models import Order, OrderItem, ShopSettings


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["subtotal"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number",
        "user",
        "status",
        "payment_status",
        "shipping_method",
        "total",
        "item_count",
        "created_at",
    ]
    list_filter = ["status", "payment_status", "shipping_method", "created_at"]
    search_fields = ["order_number", "user__phone", "shipping_phone"]
    inlines = [OrderItemInline]
    readonly_fields = ["order_number", "payment_ref_id", "payment_card_pan", "paid_at", "created_at", "updated_at"]
    list_editable = ["status", "payment_status"]
    list_per_page = 50
    fieldsets = (
        (None, {
            "fields": ("order_number", "user", "status", "payment_status")
        }),
        ("Shipping Information", {
            "fields": (
                "shipping_address",
                "shipping_city",
                "shipping_state",
                "shipping_zip",
                "shipping_country",
                "shipping_phone",
                "shipping_method",
                "tracking_code",
            )
        }),
        ("Payment", {
            "fields": ("payment_gateway", "payment_authority", "payment_ref_id", "payment_card_pan", "paid_at")
        }),
        ("Financial", {
            "fields": ("subtotal", "shipping_cost", "discount", "total")
        }),
        ("Notes", {
            "fields": ("notes",),
            "classes": ("collapse",)
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = "Items"


@admin.register(ShopSettings)
class ShopSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not ShopSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
