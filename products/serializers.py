import json

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from .models import Category, Product, ProductImage, ProductSize, SizeGuide, Sport, validate_size_guide_table

MAX_SIZES_PER_PRODUCT = 30


class ProductSizeSerializer(serializers.ModelSerializer):
    in_stock = serializers.SerializerMethodField()

    class Meta:
        model = ProductSize
        fields = ["id", "label", "stock", "in_stock"]

    def get_in_stock(self, obj):
        return obj.stock > 0


class SizeGuideSerializer(serializers.ModelSerializer):
    class Meta:
        model = SizeGuide
        fields = ["id", "title_fa", "title_en", "how_to_measure_fa", "how_to_measure_en", "image", "columns", "rows"]


def active_sizes(product):
    """Active sizes in display order, from the prefetch cache when there is one."""
    return [s for s in product.sizes.all() if s.is_active]


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
            "show_on_home",
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
            "meta_title", "meta_description", "is_active", "show_on_home", "product_count", "created_at",
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
    size_labels = serializers.SerializerMethodField()

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
            "size_labels",
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

    def get_size_labels(self, obj):
        # A product with sizes must be added to the cart from its page, where a size is chosen.
        return [s.label for s in active_sizes(obj)]


class SportBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sport
        fields = ["id", "name", "name_fa", "slug"]


class ProductDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    rating_average = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()
    sports = SportBriefSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    name_localized = serializers.SerializerMethodField()
    description_localized = serializers.SerializerMethodField()
    sizes = serializers.SerializerMethodField()
    size_guide = SizeGuideSerializer(read_only=True)

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
            "sizes",
            "size_guide",
            "injury_type",
            "brand",
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
            "meta_title",
            "meta_description",
            "rating_average",
            "rating_count",
        ]

    def _ratings(self, obj):
        if not hasattr(obj, "_rating_stats"):
            from django.db.models import Avg, Count

            obj._rating_stats = obj.reviews.aggregate(avg=Avg("rating"), count=Count("id"))
        return obj._rating_stats

    def get_rating_average(self, obj):
        avg = self._ratings(obj)["avg"]
        return round(avg, 1) if avg else None

    def get_rating_count(self, obj):
        return self._ratings(obj)["count"]

    def get_sizes(self, obj):
        return ProductSizeSerializer(active_sizes(obj), many=True).data

    def get_name_localized(self, obj):
        lang = self.context.get('lang', 'en')
        return obj.get_name(lang)

    def get_description_localized(self, obj):
        lang = self.context.get('lang', 'en')
        return obj.get_description(lang)


class ProductSizeAdminSerializer(serializers.ModelSerializer):
    """A size as staff edit it. Sent as a list on the product; an id updates, no id creates."""

    id = serializers.IntegerField(required=False)

    class Meta:
        model = ProductSize
        fields = ["id", "label", "sku", "stock", "sort_order", "is_active"]
        # Uniqueness is checked across the whole list in ProductCreateSerializer.validate_sizes.
        validators = []

    def validate_label(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Enter a size name.")
        return value

    def validate_sku(self, value):
        return value.strip()


class JSONOrTextField(serializers.JSONField):
    """JSON from a JSON body, or JSON text from a multipart form (so a diagram can be sent with it)."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                raise serializers.ValidationError("Value must be valid JSON.")
        return super().to_internal_value(data)


class SizeGuideAdminSerializer(serializers.ModelSerializer):
    columns = JSONOrTextField()
    rows = JSONOrTextField()
    image = serializers.ImageField(required=False, allow_null=True)
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = SizeGuide
        fields = [
            "id", "name", "title_fa", "title_en", "how_to_measure_fa", "how_to_measure_en", "image",
            "columns", "rows", "product_count", "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]

    def get_product_count(self, obj):
        return obj.products.count()

    def validate(self, attrs):
        columns = attrs.get("columns", getattr(self.instance, "columns", None))
        rows = attrs.get("rows", getattr(self.instance, "rows", None))
        try:
            validate_size_guide_table(columns, rows)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.message_dict)
        return attrs


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
            "sizes",
            "size_guide",
            "size_guide_name",
            "injury_type",
            "brand",
            "color",
            "weight",
            "material",
            "meta_title",
            "meta_description",
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
    sizes = ProductSizeAdminSerializer(many=True, read_only=True)
    size_guide_name = serializers.CharField(source="size_guide.name", read_only=True, default=None)

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
    # Omit `sizes` to leave them as they are; send [] to sell the product without sizes.
    sizes = ProductSizeAdminSerializer(many=True, required=False)

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
            "sizes",
            "size_guide",
            "injury_type",
            "brand",
            "color",
            "weight",
            "material",
            "meta_title",
            "meta_description",
            "is_active",
            "is_featured",
        ]
        # The slug is generated from the name on create and used as the lookup key.
        read_only_fields = ["id", "slug"]

    def validate_sizes(self, sizes):
        if len(sizes) > MAX_SIZES_PER_PRODUCT:
            raise serializers.ValidationError(f"A product can have at most {MAX_SIZES_PER_PRODUCT} sizes.")
        labels = [s["label"].lower() for s in sizes]
        dupes = {label for label in labels if labels.count(label) > 1}
        if dupes:
            raise serializers.ValidationError(f"Each size can appear once: {', '.join(sorted(dupes))}.")
        own_ids = set(self.instance.sizes.values_list("id", flat=True)) if self.instance else set()
        if any(s.get("id") and s["id"] not in own_ids for s in sizes):
            raise serializers.ValidationError("A size does not belong to this product.")
        skus = [s["sku"] for s in sizes if s.get("sku")]
        if len(skus) != len(set(skus)):
            raise serializers.ValidationError("Each SKU can be used once.")
        taken = ProductSize.objects.filter(sku__in=skus)
        if self.instance:
            taken = taken.exclude(product=self.instance)
        if taken.exists():
            raise serializers.ValidationError(f"SKU already used by another product: {taken.first().sku}.")
        return sizes

    @transaction.atomic
    def create(self, validated_data):
        sizes = validated_data.pop("sizes", None)
        product = super().create(validated_data)
        if sizes:
            save_sizes(product, sizes)
        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        sizes = validated_data.pop("sizes", None)
        product = super().update(instance, validated_data)
        if sizes is not None:
            save_sizes(product, sizes)
            if not sizes and "stock" in validated_data:  # back to one size: the typed stock counts
                Product.objects.filter(pk=product.pk).update(stock=validated_data["stock"])
        product.refresh_from_db(fields=["stock"])
        return product


def save_sizes(product, sizes):
    """Make the product's sizes match `sizes`: update by id, create without id, delete the rest.

    Deleting a size keeps past orders (order_items keeps its label) and removes it from carts.
    """
    existing = {s.id: s for s in product.sizes.all()}
    keep = {s["id"] for s in sizes if s.get("id")}
    ProductSize.objects.filter(product=product).exclude(id__in=keep).delete()
    # Park renamed labels first, so swapping two labels (S <-> M) never breaks the unique rule.
    for data in sizes:
        size = existing.get(data.get("id"))
        if size and size.label.lower() != data["label"].lower():
            ProductSize.objects.filter(pk=size.pk).update(label=f"~{size.pk}")
    for order, data in enumerate(sizes):
        fields = {
            "label": data["label"], "sku": data.get("sku", ""), "stock": data.get("stock", 0),
            "sort_order": data.get("sort_order", order), "is_active": data.get("is_active", True),
        }
        if data.get("id"):
            ProductSize.objects.filter(pk=data["id"]).update(**fields)
        else:
            ProductSize.objects.create(product=product, **fields)
    product.refresh_stock()  # .update() skips the sync signal
