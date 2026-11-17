"""Who may use which part of the staff portal (/admin-portal).

Superusers can do everything. Other staff need Django permissions, which the owner hands out
in Django admin by adding them to a group (see accounts/management/commands/setup_roles.py):
- catalog (products, categories, photos, prices): products.change_product
- shop (orders, customers, stats, shop settings): orders.change_order
Deleting through the catalog API also needs that model's delete permission.
"""
from rest_framework.permissions import BasePermission

CATALOG_PERMISSION = "products.change_product"
SHOP_PERMISSION = "orders.change_order"


def _staff_with(user, perm):
    if not (user and user.is_authenticated and user.is_active and user.is_staff):
        return False
    return user.is_superuser or user.has_perm(perm)


def can_manage_catalog(user):
    return _staff_with(user, CATALOG_PERMISSION)


def can_manage_shop(user):
    return _staff_with(user, SHOP_PERMISSION)


def can_delete(user, model):
    meta = model._meta
    return user.is_superuser or user.has_perm(f"{meta.app_label}.delete_{meta.model_name}")


def admin_access(user):
    return {"catalog": can_manage_catalog(user), "shop": can_manage_shop(user)}


class CanManageCatalog(BasePermission):
    """Catalog staff. A view can map an action to the model its DELETE removes (`delete_models`)."""

    def has_permission(self, request, view):
        if not can_manage_catalog(request.user):
            return False
        if request.method == "DELETE":
            model = getattr(view, "delete_models", {}).get(view.action) or view.get_queryset().model
            return can_delete(request.user, model)
        return True


class CanManageShop(BasePermission):
    def has_permission(self, request, view):
        return can_manage_shop(request.user)
