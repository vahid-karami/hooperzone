from django.urls import path

from . import admin_views, views

app_name = "orders"

urlpatterns = [
    path("", views.order_list, name="order-list"),
    path("create/", views.order_create, name="order-create"),
    path("payment/verify/", views.order_pay_verify, name="order-pay-verify"),
    path("shipping-methods/", views.shipping_methods, name="shipping-methods"),
    path("shop-info/", views.shop_info, name="shop-info"),
    # Staff endpoints; must come before the <order_number> patterns.
    path("admin/stats/", admin_views.admin_stats, name="admin-stats"),
    path("admin/settings/", admin_views.admin_shop_settings, name="admin-settings"),
    path("admin/export.csv", admin_views.admin_order_export, name="admin-order-export"),
    path("admin/bulk-status/", admin_views.admin_order_bulk_status, name="admin-order-bulk-status"),
    path("admin/", admin_views.admin_order_list, name="admin-order-list"),
    path("admin/<str:order_number>/", admin_views.admin_order_update, name="admin-order-update"),
    path("<str:order_number>/", views.order_detail, name="order-detail"),
    path("<str:order_number>/cancel/", views.order_cancel, name="order-cancel"),
    path("<str:order_number>/pay/", views.order_pay_initiate, name="order-pay-initiate"),
]
