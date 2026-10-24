import os

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from products.models import Product, ProductImage

# Product photos shipped with the repo, named after the product slug.
IMAGES_DIR = os.path.join(settings.BASE_DIR, "frontend", "public", "images", "products")

# Used for products that have no photo of their own.
FALLBACK_BY_INJURY_TYPE = {
    "knee": "performance-knee-sleeve.jpg",
    "ankle": "ankle-stabilizer-brace.jpg",
    "back": "lumbar-sports-support.jpg",
    "neck": "lumbar-sports-support.jpg",
    "shoulder": "shoulder-support-brace.jpg",
    "wrist": "wrist-stabilizer.jpg",
    "elbow": "tennis-elbow-support.jpg",
    "hip": "lumbar-sports-support.jpg",
    "general": "compression-calf-sleeve.jpg",
}


class Command(BaseCommand):
    help = "Attach the product photos in hooperzone/frontend/public/images/products to products"

    def handle(self, *args, **kwargs):
        ProductImage.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("Cleared existing product images."))

        for product in Product.objects.all():
            filename = f"{product.slug}.jpg"
            path = os.path.join(IMAGES_DIR, filename)
            if not os.path.exists(path):
                filename = FALLBACK_BY_INJURY_TYPE.get(product.injury_type, FALLBACK_BY_INJURY_TYPE["general"])
                path = os.path.join(IMAGES_DIR, filename)
            if not os.path.exists(path):
                self.stdout.write(self.style.WARNING(f"Image not found for {product.slug}"))
                continue

            with open(path, "rb") as f:
                ProductImage.objects.create(
                    product=product,
                    image=File(f, name=f"{product.slug}.jpg"),
                    alt_text=product.name,
                    is_primary=True,
                )
            self.stdout.write(f"Added image for product: {product.slug}")

        self.stdout.write(self.style.SUCCESS("Successfully seeded product images!"))
