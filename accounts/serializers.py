from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import serializers

from hooperzone.fields import DigitsCharField, normalize_digits
from hooperzone.permissions import admin_access

from .passwords import check_password_rules

User = get_user_model()


def coded_error(code, message, field="non_field_errors"):
    """A validation error the storefront can translate: the usual field message plus a stable `code`."""
    return serializers.ValidationError({field: [message], "code": code})


class UserRegistrationSerializer(serializers.Serializer):
    username = DigitsCharField(max_length=150, required=False, allow_blank=True)
    phone = DigitsCharField(max_length=50, required=False, allow_blank=True)
    # Length and the other rules are checked in validate() (check_password_rules), so a short
    # password is reported with a rule code like every other refused password.
    password = serializers.CharField(write_only=True, max_length=128)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    # From otp/verify (register): proves the caller received the code for this phone.
    registration_token = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, data):
        username = data.get("username", "").strip()
        phone = data.get("phone", "").strip()

        if not username and not phone:
            raise serializers.ValidationError("Either username or phone number is required.")

        if username:
            existing = User.objects.filter(Q(username__iexact=username) | Q(phone__iexact=username)).first()
            if existing and existing.has_usable_password():
                raise serializers.ValidationError({"username": "A user with this username already exists."})

        if phone:
            existing = User.objects.filter(Q(phone__iexact=phone) | Q(username__iexact=phone)).first()
            if existing and existing.has_usable_password():
                raise serializers.ValidationError({"phone": "A user with this phone number already exists."})

        # Last, so "already registered" is reported before anything about the password.
        check_password_rules(
            data["password"],
            username=username or phone,
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            email=data.get("email", ""),
        )
        return data


class OTPSendSerializer(serializers.Serializer):
    phone = DigitsCharField(max_length=15)
    otp_type = serializers.ChoiceField(
        choices=["register", "login", "reset_password"],
        default="register"
    )


class OTPVerifySerializer(serializers.Serializer):
    phone = DigitsCharField(max_length=15)
    code = DigitsCharField(max_length=6)
    otp_type = serializers.ChoiceField(
        choices=["register", "login", "reset_password"],
        default="register"
    )


class PasswordResetSerializer(serializers.Serializer):
    phone = DigitsCharField(max_length=15)
    code = DigitsCharField(max_length=6)
    # The rules (length included) are checked in the view with check_password_rules.
    new_password = serializers.CharField(write_only=True, max_length=128)


class UserProfileSerializer(serializers.ModelSerializer):
    # Which staff-portal sections this user may open: {"catalog": bool, "shop": bool}.
    admin_access = serializers.SerializerMethodField()
    address = serializers.CharField(max_length=500, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "phone", "email", "first_name", "last_name", "date_joined",
            "address", "province", "city", "postal_code", "is_staff", "admin_access",
        ]
        read_only_fields = ["id", "date_joined", "is_staff"]

    def get_admin_access(self, user):
        return admin_access(user)

    def _others(self):
        return User.objects.exclude(pk=getattr(self.instance, "pk", None))

    def validate_phone(self, value):
        # The model's unique check ran on the raw input; re-check after normalizing digits.
        # People sign in with phone or username, so neither may equal someone else's other one.
        value = normalize_digits(value)
        if value and self._others().filter(Q(phone=value) | Q(username__iexact=value)).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def validate_username(self, value):
        # Taking a stranger's phone number as a username would block them from registering
        # with it and get in the way of their login.
        value = normalize_digits(value)
        if value and self._others().filter(Q(username__iexact=value) | Q(phone__iexact=value)).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def update(self, instance, validated_data):
        # A new number has not been proven by a code yet.
        if "phone" in validated_data and validated_data["phone"] != instance.phone:
            instance.is_verified = False
        return super().update(instance, validated_data)


class UserLoginSerializer(serializers.Serializer):
    username = DigitsCharField(max_length=150, required=False, allow_blank=True)
    phone = DigitsCharField(max_length=50, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        from django.contrib.auth import authenticate

        identifier = data.get("username", "").strip() or data.get("phone", "").strip()
        if not identifier:
            raise coded_error("identifier_required", "Please provide a username or phone number.")

        user = authenticate(username=identifier, phone=identifier, password=data["password"])
        if not user:
            # One answer for a wrong password and an unknown name: don't reveal which accounts exist.
            raise coded_error("invalid_credentials", "Invalid username/phone or password.")

        data["user"] = user
        return data
