from django.core.management.base import BaseCommand

from products.watermark import sync_watermarks


class Command(BaseCommand):
    help = (
        "Put the shop logo on product photos that don't have it yet, or take it off again if the "
        "logo is switched off in the shop settings. The clean uploads are kept, so this can be undone."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true",
            help="Render the logo again on every photo from the clean originals (after changing the logo file).",
        )
        parser.add_argument(
            "--remove", action="store_true", help="Take the logo off every photo, whatever the shop setting says.",
        )

    def handle(self, *args, **options):
        if options["remove"]:
            count = sync_watermarks(enabled=False)
            self.stdout.write(f"Removed the logo from {count} product photo(s).")
            return
        count = sync_watermarks(force=options["force"])
        self.stdout.write(f"Updated the logo on {count} product photo(s).")
