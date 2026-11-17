from django.core.management.base import BaseCommand

from orders.services import cancel_unpaid_orders


class Command(BaseCommand):
    help = "Cancel unpaid orders older than the timeout in shop settings and release their stock."

    def add_arguments(self, parser):
        parser.add_argument("--minutes", type=int, help="Override the timeout from shop settings.")

    def handle(self, *args, **options):
        count = cancel_unpaid_orders(options.get("minutes"))
        self.stdout.write(f"Cancelled {count} unpaid order(s).")
