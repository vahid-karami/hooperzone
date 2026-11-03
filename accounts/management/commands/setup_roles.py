from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

# Staff who add and edit products, photos, categories and prices in /admin-portal (and Django
# admin), without seeing orders, customers or shop settings (hooperzone/permissions.py).
# They can't delete products or categories; give a person products.delete_product in Django
# admin if they should.
PRODUCT_EDITORS = "Product editors"
PRODUCT_EDITOR_PERMISSIONS = [
    f"{action}_{model}"
    for model in ("product", "productimage", "category", "sport")
    for action in ("add", "change", "view")
] + ["delete_productimage"]


class Command(BaseCommand):
    help = "Create or update the staff groups (Product editors). Safe to run on every start."

    def handle(self, *args, **kwargs):
        group, created = Group.objects.get_or_create(name=PRODUCT_EDITORS)
        perms = Permission.objects.filter(content_type__app_label="products", codename__in=PRODUCT_EDITOR_PERMISSIONS)
        group.permissions.set(perms)
        verb = "Created" if created else "Updated"
        self.stdout.write(f"{verb} group '{PRODUCT_EDITORS}' ({perms.count()} permissions).")
