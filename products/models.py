import io
import logging
from pathlib import Path

from django.core.files.base import ContentFile
from django.db import models
from django.db.models.signals import post_delete
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
    name = f"{Path(image_field.name).stem}-thumb.webp"
    return ContentFile(buf.getvalue(), name=name)


class Category(models.Model):
    name = models.CharField(max_length=100)
    name_fa = models.CharField(max_length=100, blank=True, verbose_name="Name (Persian)")
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    description_fa = models.TextField(blank=True, verbose_name="Description (Persian)")
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
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


class Sport(models.Model):
    """An activity customers shop by (running, football, ...)."""

    name = models.CharField(max_length=100)
    name_fa = models.CharField(max_length=100, blank=True, verbose_name="Name (Persian)")
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to="sports/", blank=True, null=True)
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
    stock = models.PositiveIntegerField(default=0)
    injury_type = models.CharField(max_length=20, choices=INJURY_TYPE_CHOICES, default=INJURY_TYPE_GENERAL)
    brand = models.CharField(max_length=100, blank=True)
    size = models.CharField(max_length=20, blank=True, help_text="e.g., S, M, L, XL or One Size")
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
