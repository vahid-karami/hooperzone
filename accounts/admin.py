from django.contrib import admin

from .models import OTPCode, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["phone", "first_name", "last_name", "email", "is_verified", "is_staff", "date_joined"]
    list_filter = ["is_verified", "is_staff", "is_active", "date_joined"]
    search_fields = ["phone", "first_name", "last_name", "email"]
    readonly_fields = ["date_joined", "last_login"]
    fieldsets = (
        (None, {
            "fields": ("phone", "email", "first_name", "last_name")
        }),
        ("Permissions", {
            "fields": ("is_active", "is_staff", "is_superuser", "is_verified")
        }),
        ("Important Dates", {
            "fields": ("last_login", "date_joined")
        }),
    )


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ["user", "code", "otp_type", "is_used", "is_expired_display", "created_at"]
    list_filter = ["otp_type", "is_used", "created_at"]
    search_fields = ["user__phone", "code"]
    readonly_fields = ["created_at"]

    def is_expired_display(self, obj):
        return obj.is_expired()
    is_expired_display.boolean = True
    is_expired_display.short_description = "Expired"
