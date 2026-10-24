from django.contrib.auth import get_user_model
from rest_framework import serializers

from hooperzone.fields import DigitsCharField, normalize_digits

User = get_user_model()


class UserRegistrationSerializer(serializers.Serializer):
    username = DigitsCharField(max_length=150, required=False, allow_blank=True)
    phone = DigitsCharField(max_length=50, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    def validate(self, data):
        from django.db.models import Q

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
    new_password = serializers.CharField(write_only=True, min_length=8)


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "username", "phone", "email", "first_name", "last_name", "date_joined",
            "address", "province", "city", "postal_code", "is_staff",
        ]
        read_only_fields = ["id", "date_joined", "is_staff"]

    def validate_phone(self, value):
        # The model's unique check ran on the raw input; re-check after normalizing digits.
        value = normalize_digits(value)
        if value and User.objects.filter(phone=value).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value


class UserLoginSerializer(serializers.Serializer):
    username = DigitsCharField(max_length=150, required=False, allow_blank=True)
    phone = DigitsCharField(max_length=50, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        from django.contrib.auth import authenticate

        identifier = data.get("username", "").strip() or data.get("phone", "").strip()
        if not identifier:
            raise serializers.ValidationError("Please provide a username or phone number.")

        user = authenticate(username=identifier, phone=identifier, password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid username/phone or password.")

        data["user"] = user
        return data
