from django.core.management import call_command
from django.core.management.base import BaseCommand

from products.models import Product


class Command(BaseCommand):
    help = "Load the Persian demo catalogue (products, images, categories, sports) if the shop is empty"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Seed even if products already exist")

    def handle(self, *args, force=False, **kwargs):
        if Product.objects.exists() and not force:
            self.stdout.write("Products already exist; skipping demo seed.")
            return

        for command in ("seed_persian_products", "seed_product_images", "seed_category_images", "seed_sports"):
            self.stdout.write(f"Running {command}...")
            call_command(command, stdout=self.stdout)
        call_command("seed_size_guides", attach=True, stdout=self.stdout)

        self.stdout.write(self.style.SUCCESS("Demo store ready."))
