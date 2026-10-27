from django.core.management.base import BaseCommand

from products.models import ProductImage


class Command(BaseCommand):
    help = "Create WebP thumbnails for product images that don't have one (or all with --all)."

    def add_arguments(self, parser):
        parser.add_argument("--all", action="store_true", help="Rebuild every thumbnail.")

    def handle(self, *args, **options):
        images = ProductImage.objects.all()
        if not options["all"]:
            images = images.filter(thumbnail="")
        count = 0
        for image in images.iterator():
            image.refresh_thumbnail()
            count += 1
        self.stdout.write(f"Built {count} thumbnail(s).")
