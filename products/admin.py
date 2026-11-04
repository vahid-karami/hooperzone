from django.contrib import admin

from .models import Category, Product, ProductImage, ProductSize, SizeGuide, Sport


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 0
    fields = ["label", "stock", "sku", "sort_order", "is_active"]


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


@admin.register(SizeGuide)
class SizeGuideAdmin(admin.ModelAdmin):
    list_display = ["name", "title_fa", "product_count", "updated_at"]
    search_fields = ["name", "title_fa", "title_en"]

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = "Products"


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
    list_editable = ["price", "is_active", "is_featured"]
    list_per_page = 50
    autocomplete_fields = ["category"]
    filter_horizontal = ["sports"]
    inlines = [ProductSizeInline, ProductImageInline]
    fieldsets = (
        (None, {
            "fields": ("name", "slug", "category", "brand", "description")
        }),
        ("Pricing & Stock", {
            "fields": ("price", "discount_price", "stock"),
            "description": "With sizes, stock is the total of the sizes below and is set automatically.",
        }),
        ("Classification", {
            "fields": ("injury_type", "sports", "size_guide", "color", "material", "weight")
        }),
        ("Display Options", {
            "fields": ("is_active", "is_featured")
        }),
    )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.refresh_stock()  # a stock typed above must not override the sizes' total
