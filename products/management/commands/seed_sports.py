import os
import re

from django.core.files import File
from django.core.management.base import BaseCommand

from products.models import Product, Sport

from .seed_product_images import IMAGES_DIR

# Real sport photos shipped with the repo: <slug>.jpg (resized; originals stay in the admin).
SPORT_PHOTOS_DIR = os.path.join(os.path.dirname(IMAGES_DIR), "sports")


def is_seed_default(sport):
    """True when the sport has no image or only the generic cover this command made before."""
    return not sport.image or re.fullmatch(rf"sports/{sport.slug}(_\w+)?\.jpg", sport.image.name) is not None


# slug, English name, Persian name, injury types whose products suit the sport, cover photo
SPORTS = [
    ("running", "Running", "دویدن", ["knee", "ankle", "general"], "compression-calf-sleeve.jpg"),
    ("football", "Football", "فوتبال", ["knee", "ankle"], "premium-knee-stabilizer.jpg"),
    ("basketball", "Basketball", "بسکتبال", ["ankle", "knee", "wrist"], "premium-ankle-stabilizer.jpg"),
    ("volleyball", "Volleyball", "والیبال", ["ankle", "knee", "shoulder", "wrist"], "shoulder-support-brace.jpg"),
    ("tennis", "Tennis", "تنیس", ["elbow", "wrist", "shoulder"], "tennis-elbow-support.jpg"),
    ("fitness", "Fitness & Gym", "بدنسازی و فیتنس", ["back", "wrist", "shoulder", "knee"], "wrist-stabilizer.jpg"),
    ("cycling", "Cycling", "دوچرخه‌سواری", ["knee", "back"], "lumbar-sports-support.jpg"),
    ("hiking", "Hiking", "کوهنوردی", ["ankle", "knee", "general"], "full-ankle-stabilizer.jpg"),
]


class Command(BaseCommand):
    help = "Create the sports list (with photos) and link existing products to sports by injury type"

    def handle(self, *args, **kwargs):
        for order, (slug, name, name_fa, injury_types, cover) in enumerate(SPORTS):
            sport, created = Sport.objects.update_or_create(
                slug=slug,
                defaults={"name": name, "name_fa": name_fa, "sort_order": order, "is_active": True},
            )
            cover_path = os.path.join(IMAGES_DIR, cover)
            if not sport.image and os.path.exists(cover_path):
                with open(cover_path, "rb") as f:
                    sport.image.save(f"{slug}.jpg", File(f), save=True)
            photo_path = os.path.join(SPORT_PHOTOS_DIR, f"{slug}.jpg")
            if os.path.exists(photo_path) and is_seed_default(sport):
                with open(photo_path, "rb") as f:
                    sport.image.save(f"{slug}-photo.jpg", File(f), save=True)
            products = Product.objects.filter(injury_type__in=injury_types)
            sport.products.add(*products)
            action = "Created" if created else "Updated"
            self.stdout.write(f"{action} {slug}: {products.count()} products")

        self.stdout.write(self.style.SUCCESS("Sports seeded."))
