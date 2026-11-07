import io
import logging
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import models
from django.db.models import Q, Sum
from django.db.models.functions import Lower
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.text import slugify

logger = logging.getLogger(__name__)

THUMBNAIL_SIZE = (600, 600)


def make_thumbnail(image_field):
    """A WebP copy of `image_field` no larger than THUMBNAIL_SIZE, or None if it can't be read."""
    from PIL import Image, ImageOps

    try:
        image_field.open("rb")
        with Image.open(image_field) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB")
            img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, "WEBP", quality=82, method=6)
    except Exception:
        logger.warning("Could not create a thumbnail for %s", image_field.name, exc_info=True)
        return None
    finally:
        image_field.close()  # an open handle leaks, and on Windows it blocks deleting the photo
    name = f"{Path(image_field.name).stem}-thumb.webp"
    return ContentFile(buf.getvalue(), name=name)


class ThumbnailMixin(models.Model):
    """Keeps `thumbnail` (a small WebP copy of `image`) in step with the uploaded photo."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        image_changed = self._state.adding or bool(self.image) != bool(self.thumbnail) or (
            self.pk and type(self).objects.filter(pk=self.pk).exclude(image=self.image.name or "").exists()
        )
        super().save(*args, **kwargs)
        if image_changed:
            self.refresh_thumbnail()

    def refresh_thumbnail(self):
        old = self.thumbnail.name if self.thumbnail else ""
        thumb = make_thumbnail(self.image) if self.image else None
        if thumb is None and self.image:
            return  # unreadable photo: keep whatever thumbnail there was
        if old:
            self.thumbnail.storage.delete(old)
        if thumb is None:
            self.thumbnail = None
        else:
            self.thumbnail.save(thumb.name, thumb, save=False)
        type(self).objects.filter(pk=self.pk).update(thumbnail=self.thumbnail.name if self.thumbnail else "")

    @property
    def thumbnail_url(self):
        """The thumbnail, else the full photo until a thumbnail exists."""
        field = self.thumbnail or self.image
        return field.url if field else None


class Category(ThumbnailMixin):
    name = models.CharField(max_length=100)
    name_fa = models.CharField(max_length=100, blank=True, verbose_name="Name (Persian)")
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    description_fa = models.TextField(blank=True, verbose_name="Description (Persian)")
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    # Small WebP copy for the home page circles and category cards; generated on save.
    thumbnail = models.ImageField(upload_to="categories/thumbs/", blank=True, editable=False)
    show_on_home = models.BooleanField(
        default=False, help_text="Show as a highlighted circle on the home page"
    )
    meta_title = models.CharField(max_length=70, blank=True, help_text="Search result title (optional)")
    meta_description = models.CharField(max_length=170, blank=True, help_text="Search result snippet (optional)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_name(self, lang='en'):
        if lang == 'fa' and self.name_fa:
            return self.name_fa
        return self.name

    def get_description(self, lang='en'):
        if lang == 'fa' and self.description_fa:
            return self.description_fa
        return self.description


class Sport(ThumbnailMixin):
    """An activity customers shop by (running, football, ...)."""

    name = models.CharField(max_length=100)
    name_fa = models.CharField(max_length=100, blank=True, verbose_name="Name (Persian)")
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to="sports/", blank=True, null=True)
    thumbnail = models.ImageField(upload_to="sports/thumbs/", blank=True, editable=False)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "sports"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def get_name(self, lang='en'):
        if lang == 'fa' and self.name_fa:
            return self.name_fa
        return self.name


SIZE_GUIDE_MAX_COLUMNS = 6
SIZE_GUIDE_MAX_ROWS = 30


def validate_size_guide_table(columns, rows):
    """Check a size guide's table. Raises ValidationError with a field -> message dict.

    columns: [{"label_fa": "دور ران", "label_en": "Thigh", "unit": "cm"}, ...]
    rows:    [{"size": "M", "values": ["44-47", "34-37"]}, ...]  (one value per column)
    """
    if not isinstance(columns, list) or not 1 <= len(columns) <= SIZE_GUIDE_MAX_COLUMNS:
        raise ValidationError({"columns": f"Add between 1 and {SIZE_GUIDE_MAX_COLUMNS} measurement columns."})
    for col in columns:
        if not isinstance(col, dict) or not str(col.get("label_fa") or col.get("label_en") or "").strip():
            raise ValidationError({"columns": "Every column needs a name."})
        extra = set(col) - {"label_fa", "label_en", "unit"}
        if extra:
            raise ValidationError({"columns": f"Unknown column keys: {', '.join(sorted(extra))}."})
    if not isinstance(rows, list) or not 1 <= len(rows) <= SIZE_GUIDE_MAX_ROWS:
        raise ValidationError({"rows": f"Add between 1 and {SIZE_GUIDE_MAX_ROWS} size rows."})
    seen = set()
    for row in rows:
        size = str(row.get("size", "")).strip() if isinstance(row, dict) else ""
        values = row.get("values") if isinstance(row, dict) else None
        if not size or len(size) > 20:
            raise ValidationError({"rows": "Every row needs a size name of at most 20 characters."})
        if size.lower() in seen:
            raise ValidationError({"rows": f"Size {size} appears twice."})
        seen.add(size.lower())
        if not isinstance(values, list) or len(values) != len(columns):
            raise ValidationError({"rows": f"Size {size} needs exactly one value per column."})
        if any(not isinstance(v, (str, int, float)) or len(str(v)) > 40 for v in values):
            raise ValidationError({"rows": f"Size {size} has a value that is too long."})


class SizeGuide(models.Model):
    """A reusable measurement chart (راهنمای سایز), shared by the products of one line.

    The table is shown to customers and always edited as a whole, so it is stored as validated
    JSON (columns + rows). Sellable sizes and their stock live in ProductSize instead.
    """

    name = models.CharField(max_length=100, unique=True, help_text="Internal name, e.g. 'Knee sleeves'")
    title_fa = models.CharField(max_length=150, blank=True, verbose_name="Title (Persian)")
    title_en = models.CharField(max_length=150, blank=True, verbose_name="Title (English)")
    how_to_measure_fa = models.TextField(blank=True, verbose_name="How to measure (Persian)")
    how_to_measure_en = models.TextField(blank=True, verbose_name="How to measure (English)")
    image = models.ImageField(upload_to="size-guides/", blank=True, null=True, help_text="Measuring diagram")
    columns = models.JSONField(default=list)
    rows = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "size_guides"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        validate_size_guide_table(self.columns, self.rows)


class Product(models.Model):
    INJURY_TYPE_KNEE = "knee"
    INJURY_TYPE_ANKLE = "ankle"
    INJURY_TYPE_BACK = "back"
    INJURY_TYPE_NECK = "neck"
    INJURY_TYPE_SHOULDER = "shoulder"
    INJURY_TYPE_WRIST = "wrist"
    INJURY_TYPE_ELBOW = "elbow"
    INJURY_TYPE_HIP = "hip"
    INJURY_TYPE_GENERAL = "general"

    INJURY_TYPE_CHOICES = [
        (INJURY_TYPE_KNEE, "Knee Support"),
        (INJURY_TYPE_ANKLE, "Ankle Support"),
        (INJURY_TYPE_BACK, "Back Support"),
        (INJURY_TYPE_NECK, "Neck Support"),
        (INJURY_TYPE_SHOULDER, "Shoulder Support"),
        (INJURY_TYPE_WRIST, "Wrist Support"),
        (INJURY_TYPE_ELBOW, "Elbow Support"),
        (INJURY_TYPE_HIP, "Hip Support"),
        (INJURY_TYPE_GENERAL, "General Support"),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products")
    sports = models.ManyToManyField(Sport, blank=True, related_name="products")
    name = models.CharField(max_length=200)
    name_fa = models.CharField(max_length=200, blank=True, verbose_name="Name (Persian)")
    slug = models.SlugField(unique=True)
    description = models.TextField()
    description_fa = models.TextField(blank=True, verbose_name="Description (Persian)")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    price_irr = models.DecimalField(max_digits=12, decimal_places=0, blank=True, null=True, verbose_name="Price (IRR)")
    cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Cost Price")
    cost_irr = models.DecimalField(max_digits=12, decimal_places=0, blank=True, null=True, verbose_name="Cost Price (IRR)")
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    discount_price_irr = models.DecimalField(max_digits=12, decimal_places=0, blank=True, null=True, verbose_name="Discount Price (IRR)")
    # With sizes, this is the total of the active sizes' stock (kept in sync by refresh_stock).
    stock = models.PositiveIntegerField(default=0)
    size_guide = models.ForeignKey(
        SizeGuide, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    injury_type = models.CharField(max_length=20, choices=INJURY_TYPE_CHOICES, default=INJURY_TYPE_GENERAL)
    brand = models.CharField(max_length=100, blank=True)
    color = models.CharField(max_length=50, blank=True)
    weight = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, help_text="Weight in grams")
    material = models.CharField(max_length=100, blank=True)
    meta_title = models.CharField(max_length=70, blank=True, help_text="Search result title (optional)")
    meta_description = models.CharField(max_length=170, blank=True, help_text="Search result snippet (optional)")
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def _unique_slug(self):
        base = slugify(self.name)[:40] or "product"
        slug, n = base, 2
        while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug, n = f"{base}-{n}", n + 1
        return slug

    def get_name(self, lang='en'):
        if lang == 'fa' and self.name_fa:
            return self.name_fa
        return self.name

    def get_description(self, lang='en'):
        if lang == 'fa' and self.description_fa:
            return self.description_fa
        return self.description

    @property
    def effective_price(self):
        return self.discount_price if self.discount_price else self.price

    @property
    def effective_price_irr(self):
        if self.discount_price_irr:
            return self.discount_price_irr
        if self.price_irr:
            return self.price_irr
        return None

    @property
    def in_stock(self):
        return self.stock > 0

    def refresh_stock(self):
        """With sizes, set stock to the sum of the active sizes' stock. Without sizes, leave it."""
        sizes = ProductSize.objects.filter(product_id=self.pk)
        if not sizes.exists():
            return
        self.stock = sizes.filter(is_active=True).aggregate(total=Sum("stock"))["total"] or 0
        Product.objects.filter(pk=self.pk).update(stock=self.stock)


class ProductSize(models.Model):
    """One size of a product that customers can buy, with its own stock."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="sizes")
    label = models.CharField(max_length=20, help_text="e.g. S, M, L, XL, 2 or 39-41")
    sku = models.CharField(max_length=64, blank=True, help_text="Warehouse code (optional, unique)")
    stock = models.PositiveIntegerField(default=0)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product_sizes"
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(Lower("label"), "product", name="unique_size_label_per_product"),
            models.UniqueConstraint(fields=["sku"], condition=~Q(sku=""), name="unique_size_sku"),
            models.CheckConstraint(condition=~Q(label=""), name="size_label_not_empty"),
            # One size per row: "M L" or "M, L" must be two rows, or the shop shows one "M L" button.
            models.CheckConstraint(
                condition=~Q(label__contains=" ") & ~Q(label__contains=",") & ~Q(label__contains="،")
                & ~Q(label__contains="/"),
                name="size_label_is_one_size",
            ),
        ]
        indexes = [models.Index(fields=["product", "is_active"])]

    def __str__(self):
        return f"{self.product.name} – {self.label}"


@receiver([post_save, post_delete], sender=ProductSize)
def sync_product_stock(sender, instance, **kwargs):
    """Keep products.stock equal to the total of the product's active sizes.

    Bulk .update() calls skip this signal; callers that use them call refresh_stock() themselves.
    """
    product = Product(pk=instance.product_id)
    if ProductSize.objects.filter(product_id=instance.product_id).exists():
        product.refresh_stock()
    elif kwargs.get("signal") is post_delete:
        Product.objects.filter(pk=instance.product_id).update(stock=0)  # last size removed


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/")
    # Small WebP copy for product cards and lists; generated on save.
    thumbnail = models.ImageField(upload_to="products/thumbs/", blank=True, editable=False)
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        image_changed = self._state.adding or not self.thumbnail or (
            self.pk and ProductImage.objects.filter(pk=self.pk).exclude(image=self.image.name).exists()
        )
        super().save(*args, **kwargs)
        if image_changed and self.image:
            self.refresh_thumbnail()

    def refresh_thumbnail(self):
        thumb = make_thumbnail(self.image)
        if thumb is None:
            return
        if self.thumbnail:
            self.thumbnail.delete(save=False)
        self.thumbnail.save(thumb.name, thumb, save=False)
        ProductImage.objects.filter(pk=self.pk).update(thumbnail=self.thumbnail.name)

    class Meta:
        db_table = "product_images"
        ordering = ["-is_primary", "-created_at"]

    def __str__(self):
        return f"Image for {self.product.name}"


@receiver(post_delete, sender=ProductImage)
def delete_product_image_files(sender, instance, **kwargs):
    """Remove the photo and its thumbnail from disk, also when a whole product is deleted."""
    for field in (instance.image, instance.thumbnail):
        if field:
            field.delete(save=False)


@receiver(post_delete, sender=Category)
@receiver(post_delete, sender=Sport)
def delete_thumbnail_file(sender, instance, **kwargs):
    if instance.thumbnail:
        instance.thumbnail.delete(save=False)
