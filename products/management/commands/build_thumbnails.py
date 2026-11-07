from django.core.management.base import BaseCommand

from products.models import Category, ProductImage, Sport


class Command(BaseCommand):
    help = "Create WebP thumbnails for product, category and sport images that don't have one (or all with --all)."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Rebuild every thumbnail.")

    def handle(self, *args, **options):
        count = 0
        for model in (ProductImage, Category, Sport):
            images = model.objects.exclude(image="").exclude(image__isnull=True)
            if not options["all"]:
                images = images.filter(thumbnail="")
            for obj in images.iterator():
                obj.refresh_thumbnail()
                count += 1
        self.stdout.write(f"Built {count} thumbnail(s).")
