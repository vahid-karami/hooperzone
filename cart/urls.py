from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_detail, name="cart-detail"),
    path("add/", views.cart_add_item, name="cart-add"),
    path("update/", views.cart_update_item, name="cart-update"),
    path("remove/", views.cart_remove_item, name="cart-remove"),
    path("clear/", views.cart_clear, name="cart-clear"),
]
