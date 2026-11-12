import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, phone=None, password=None, username=None, **extra_fields):
        identifier = phone or username or extra_fields.get("username")
        if not identifier:
            raise ValueError("Users must have a phone number or username")
        if not phone:
            phone = username
        if not username:
            username = phone
        extra_fields.setdefault("is_verified", True)
        user = self.model(phone=phone, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone=None, password=None, username=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)
        return self.create_user(phone=phone, password=password, username=username, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=50, unique=True, null=True, blank=True)
    email = models.EmailField(blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    address = models.TextField(blank=True, verbose_name="Address")
    province = models.CharField(max_length=100, blank=True, verbose_name="Province")
    city = models.CharField(max_length=100, blank=True, verbose_name="City")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="Postal Code")

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.username or self.phone or str(self.id)

    def get_full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name or self.phone

    class Meta:
        db_table = "users"


class OTPCode(models.Model):
    OTP_TYPE_REGISTER = "register"
    OTP_TYPE_LOGIN = "login"
    OTP_TYPE_RESET_PASSWORD = "reset_password"

    OTP_TYPE_CHOICES = [
        (OTP_TYPE_REGISTER, "Register"),
        (OTP_TYPE_LOGIN, "Login"),
        (OTP_TYPE_RESET_PASSWORD, "Reset Password"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otp_codes")
    code = models.CharField(max_length=6)
    otp_type = models.CharField(max_length=20, choices=OTP_TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)

    @staticmethod
    def generate_code():
        return f"{secrets.randbelow(1_000_000):06d}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_used and not self.is_expired()

    def mark_used(self):
        self.is_used = True
        self.save(update_fields=["is_used"])

    def __str__(self):
        return f"{self.user.phone} - {self.code} ({self.otp_type})"

    class Meta:
        db_table = "otp_codes"
        ordering = ["-created_at"]
