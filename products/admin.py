from django.contrib import admin

from .models import Category, Product, ProductImage, Sport


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "product_count", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}

    def product_count(self, obj):
        return obj.products.filter(is_active=True).count()
    product_count.short_description = "Active Products"


@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ["name", "name_fa", "slug", "sort_order", "is_active"]
    list_editable = ["sort_order", "is_active"]
    search_fields = ["name", "name_fa"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "brand",
        "price",
        "discount_price",
        "stock",
        "injury_type",
        "is_active",
        "is_featured",
        "created_at",
    ]
    list_filter = [
        "category",
        "injury_type",
        "is_active",
        "is_featured",
        "brand",
    ]
    search_fields = ["name", "brand", "description", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    list_editable = ["price", "stock", "is_active", "is_featured"]
    list_per_page = 50
    autocomplete_fields = ["category"]
    filter_horizontal = ["sports"]
    inlines = [ProductImageInline]
    fieldsets = (
        (None, {
            "fields": ("name", "slug", "category", "brand", "description")
        }),
        ("Pricing & Stock", {
            "fields": ("price", "discount_price", "stock")
        }),
        ("Classification", {
            "fields": ("injury_type", "sports", "color", "material", "weight")
        }),
        ("Display Options", {
            "fields": ("is_active", "is_featured")
        }),
    )
