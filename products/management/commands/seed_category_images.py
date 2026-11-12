import os

from django.core.files import File
from django.core.management.base import BaseCommand

from products.models import Category

from .seed_product_images import IMAGES_DIR

# Category slug -> cover photo shipped with the repo.
CATEGORY_IMAGES = {
    "knee-braces": "premium-knee-brace.jpg",
    "ankle-supports": "compression-ankle-sleeve.jpg",
    "back-supports": "lumbar-sports-support.jpg",
    "shoulder-supports": "adjustable-shoulder-brace.jpg",
    "wrist-elbow": "tennis-elbow-support.jpg",
    "compression-wear": "compression-calf-sleeve.jpg",
}


class Command(BaseCommand):
    help = "Give each demo category a cover photo (never replaces an image uploaded in the admin)"

    def handle(self, *args, **kwargs):
        updated = 0
        for slug, filename in CATEGORY_IMAGES.items():
            category = Category.objects.filter(slug=slug).first()
            path = os.path.join(IMAGES_DIR, filename)
            if category is None or category.image or not os.path.exists(path):
                continue
            with open(path, "rb") as f:
                category.image.save(f"{slug}.jpg", File(f), save=True)
            updated += 1
            self.stdout.write(f"Added image for category: {slug}")

        self.stdout.write(self.style.SUCCESS(f"Category images seeded ({updated} updated)."))
