from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "products"

router = DefaultRouter()
router.register("categories", views.CategoryViewSet, basename="category")
router.register("sports", views.SportViewSet, basename="sport")
router.register("", views.ProductViewSet, basename="product")
router.register("admin/products", views.ProductAdminViewSet, basename="admin-product")
router.register("admin/categories", views.CategoryAdminViewSet, basename="admin-category")

urlpatterns = [
    path("", include(router.urls)),
]
