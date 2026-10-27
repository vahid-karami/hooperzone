from rest_framework import serializers

from .models import Category, Product, ProductImage, Sport


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.SerializerMethodField()
    name_localized = serializers.SerializerMethodField()
    description_localized = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "name_fa",
            "slug",
            "description",
            "description_fa",
            "image",
            "product_count",
            "name_localized",
            "description_localized",
        ]

    def get_product_count(self, obj):
        # CategoryViewSet annotates the count so a list costs one query.
        count = getattr(obj, "active_product_count", None)
        return count if count is not None else obj.products.filter(is_active=True).count()

    def get_name_localized(self, obj):
        lang = self.context.get('lang', 'en')
        return obj.get_name(lang)

    def get_description_localized(self, obj):
        lang = self.context.get('lang', 'en')
        return obj.get_description(lang)


class SportSerializer(serializers.ModelSerializer):
    name_localized = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Sport
        fields = ["id", "name", "name_fa", "slug", "name_localized", "product_count", "cover_image"]

    def get_name_localized(self, obj):
        return obj.get_name(self.context.get("lang", "en"))

    def get_product_count(self, obj):
        return obj.products.filter(is_active=True).count()

    def get_cover_image(self, obj):
        """The sport's own image, else a photo of one of its products."""
        if obj.image:
            return obj.image.url
        image = (
            ProductImage.objects.filter(product__sports=obj, product__is_active=True)
            .order_by("-is_primary", "product__created_at")
            .first()
        )
        return image.image.url if image else None


class ProductImageSerializer(serializers.ModelSerializer):
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image", "thumbnail", "alt_text", "is_primary"]

    def get_thumbnail(self, obj):
        # Falls back to the full image until a thumbnail exists.
        return (obj.thumbnail or obj.image).url if (obj.thumbnail or obj.image) else None


class CategoryAdminSerializer(serializers.ModelSerializer):
    """Categories as staff edit them: includes inactive ones and accepts an image upload."""

    product_count = serializers.IntegerField(read_only=True, default=0)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Category
        fields = [
            "id", "name", "name_fa", "slug", "description", "description_fa", "image",
            "is_active", "product_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {"slug": {"required": False}}

    def validate(self, attrs):
        if not attrs.get("slug") and not (self.instance and self.instance.slug):
            from django.utils.text import slugify

            base = slugify(attrs.get("name", ""))[:45] or "category"
            slug, n = base, 2
            while Category.objects.filter(slug=slug).exists():
                slug, n = f"{base}-{n}", n + 1
            attrs["slug"] = slug
        return attrs


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    primary_image = serializers.SerializerMethodField()
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    name_localized = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "name_fa",
            "slug",
            "category_name",
            "price",
            "discount_price",
            "effective_price",
            "injury_type",
            "brand",
            "size",
            "primary_image",
            "in_stock",
            "is_featured",
            "name_localized",
        ]

    def get_primary_image(self, obj):
        # Sorted in Python so the viewset's prefetch_related("images") is used (no query per product).
        images = sorted(obj.images.all(), key=lambda i: (not i.is_primary, -i.created_at.timestamp()))
        return ProductImageSerializer(images[0], context=self.context).data if images else None

    def get_name_localized(self, obj):
        lang = self.context.get('lang', 'en')
        return obj.get_name(lang)


class SportBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sport
        fields = ["id", "name", "name_fa", "slug"]


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    sports = SportBriefSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    name_localized = serializers.SerializerMethodField()
    description_localized = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "name_fa",
            "slug",
            "description",
            "description_fa",
            "category",
            "sports",
            "price",
            "discount_price",
            "effective_price",
            "stock",
            "injury_type",
            "brand",
            "size",
            "color",
            "weight",
            "material",
            "images",
            "in_stock",
            "is_featured",
            "created_at",
            "updated_at",
            "name_localized",
            "description_localized",
        ]

    def get_name_localized(self, obj):
        lang = self.context.get('lang', 'en')
        return obj.get_name(lang)

    def get_description_localized(self, obj):
        lang = self.context.get('lang', 'en')
        return obj.get_description(lang)


class ProductAdminSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_name_fa = serializers.CharField(source="category.name_fa", read_only=True)
    primary_image = serializers.SerializerMethodField()
    margin = serializers.SerializerMethodField()
    margin_percent = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "name_fa",
            "slug",
            "description",
            "description_fa",
            "category",
            "category_name",
            "category_name_fa",
            "primary_image",
            "price",
            "price_irr",
            "cost",
            "cost_irr",
            "discount_price",
            "discount_price_irr",
            "stock",
            "injury_type",
            "brand",
            "size",
            "color",
            "weight",
            "material",
            "is_active",
            "is_featured",
            "in_stock",
            "margin",
            "margin_percent",
            "sports",
            "images",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "in_stock"]

    images = serializers.SerializerMethodField()

    def _sorted_images(self, obj):
        return sorted(obj.images.all(), key=lambda i: (not i.is_primary, -i.created_at.timestamp()))

    def get_primary_image(self, obj):
        image = self._sorted_images(obj)
        return (image[0].thumbnail or image[0].image).url if image else None

    def get_images(self, obj):
        return ProductImageSerializer(self._sorted_images(obj), many=True).data

    def get_margin(self, obj):
        cost = obj.cost or 0
        price = obj.effective_price
        if cost and price:
            return float(price) - float(cost)
        return None

    def get_margin_percent(self, obj):
        cost = obj.cost or 0
        price = obj.effective_price
        if cost and price and cost > 0:
            return round(((float(price) - float(cost)) / float(cost)) * 100, 1)
        return None


class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "slug",
            "name",
            "name_fa",
            "description",
            "description_fa",
            "category",
            "sports",
            "price",
            "price_irr",
            "cost",
            "cost_irr",
            "discount_price",
            "discount_price_irr",
            "stock",
            "injury_type",
            "brand",
            "size",
            "color",
            "weight",
            "material",
            "is_active",
            "is_featured",
        ]
        # The slug is generated from the name on create and used as the lookup key.
        read_only_fields = ["id", "slug"]
