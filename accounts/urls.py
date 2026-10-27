from django.urls import path

from . import admin_views, views

app_name = "accounts"

urlpatterns = [
    path("otp/send/", views.send_otp, name="otp-send"),
    path("otp/verify/", views.verify_otp, name="otp-verify"),
    path("register/", views.register, name="register"),
    path("password/reset/", views.reset_password, name="password-reset"),
    path("login/", views.login_with_password, name="login"),
    path("profile/", views.profile, name="profile"),
    path("admin/customers/", admin_views.customer_list, name="admin-customers"),
    path("admin/customers/export.csv", admin_views.customer_export, name="admin-customers-export"),
]
