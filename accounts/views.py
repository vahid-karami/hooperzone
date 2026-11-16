from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.db.models import Q
from rest_framework import status, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from hooperzone.fields import normalize_digits
from hooperzone.throttling import AuthRateThrottle, IPRateThrottle

from .models import OTPCode
from .passwords import check_password_rules
from .sms import SMSError, send_otp_sms
from .serializers import (
    OTPSendSerializer,
    OTPVerifySerializer,
    PasswordResetSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    UserLoginSerializer,
)

User = get_user_model()


class OTPRateThrottle(IPRateThrottle):
    """Per-IP limit on OTP endpoints to stop code brute-forcing and SMS flooding."""

    scope = "otp"


class OTPPhoneRateThrottle(SimpleRateThrottle):
    """Limit on codes sent to one phone number, whoever asks and from whatever address.

    The per-IP limit alone lets someone with many addresses text a stranger's phone without end
    (each SMS also costs the shop money).
    """

    scope = "otp_phone"

    def get_cache_key(self, request, view):
        phone = normalize_digits(str(request.data.get("phone") or "")).strip()
        if not phone:
            return None  # the serializer rejects the request anyway
        return self.cache_format % {"scope": self.scope, "ident": phone[:32]}


REGISTRATION_TOKEN_SALT = "accounts.registration"
REGISTRATION_TOKEN_MAX_AGE = 15 * 60  # seconds to finish the form after the code was accepted


def make_registration_token(user):
    """Signed proof, handed out when a register code is accepted, that the caller holds this phone."""
    return signing.dumps({"uid": user.pk}, salt=REGISTRATION_TOKEN_SALT)


def registration_token_matches(token, user):
    try:
        data = signing.loads(token, salt=REGISTRATION_TOKEN_SALT, max_age=REGISTRATION_TOKEN_MAX_AGE)
    except signing.BadSignature:  # also covers an expired token
        return False
    return isinstance(data, dict) and data.get("uid") == user.pk


def error_response(code, message, http_status=status.HTTP_400_BAD_REQUEST):
    """An error the storefront can translate: `code` is stable, `error` is the English text."""
    return Response({"error": message, "code": code}, status=http_status)


def validate_coded(serializer):
    """serializer.is_valid(), keeping a `code` set with serializers.coded_error as plain text.

    DRF turns every value of a serializer error into a list; the storefront expects
    {"code": "invalid_credentials"}, the same shape error_response() sends.
    """
    try:
        serializer.is_valid(raise_exception=True)
    except ValidationError as e:
        detail = e.detail
        if isinstance(detail, dict) and isinstance(detail.get("code"), list) and detail["code"]:
            raise ValidationError({**detail, "code": str(detail["code"][0])}) from e
        raise


def otp_error_response(code):
    return error_response(code, OTPCode.OTP_ERRORS[code])


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([OTPRateThrottle, OTPPhoneRateThrottle])
def send_otp(request):
    serializer = OTPSendSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    phone = serializer.validated_data["phone"]
    otp_type = serializer.validated_data["otp_type"]

    # A user without a usable password is a placeholder created by an unfinished
    # OTP registration, not a real account.
    user = User.objects.filter(phone=phone).first()
    is_registered = user is not None and user.has_usable_password()

    if otp_type == OTPCode.OTP_TYPE_REGISTER and is_registered:
        return error_response("phone_exists", "A user with this phone number already exists.")

    if otp_type in (OTPCode.OTP_TYPE_LOGIN, OTPCode.OTP_TYPE_RESET_PASSWORD) and not is_registered:
        return error_response("user_not_found", "No user found with this phone number.", status.HTTP_404_NOT_FOUND)

    if user is None:
        user = User(phone=phone, is_verified=False)
        user.set_unusable_password()
        user.save()

    OTPCode.objects.filter(user=user, otp_type=otp_type, is_used=False).update(is_used=True)

    otp = OTPCode.objects.create(user=user, otp_type=otp_type)

    # Never return the code to the client in production, otherwise anyone can
    # request a login OTP for any phone and sign in as that user.
    try:
        send_otp_sms(phone, otp.code)
    except SMSError:
        otp.mark_used()
        return error_response(
            "sms_failed", "Could not send the SMS. Please try again in a few minutes.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    data = {
        "message": "OTP sent successfully.",
        "phone": phone,
        "expires_in": "5 minutes",
    }
    if settings.OTP_RETURN_IN_RESPONSE:
        data["otp"] = otp.code
    return Response(data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([OTPRateThrottle])
@transaction.atomic
def verify_otp(request):
    serializer = OTPVerifySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    phone = serializer.validated_data["phone"]
    code = serializer.validated_data["code"]
    otp_type = serializer.validated_data["otp_type"]

    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        return error_response("user_not_found", "No user found with this phone number.", status.HTTP_404_NOT_FOUND)

    otp, error = OTPCode.check_code(user, otp_type, code)
    if error:
        return otp_error_response(error)

    otp.mark_used()

    if otp_type == OTPCode.OTP_TYPE_REGISTER:
        user.is_verified = True
        user.save(update_fields=["is_verified"])
        return Response(
            {
                "message": "Phone number verified successfully.",
                "next_step": "Please complete registration with phone and password.",
                # Send this back with the registration form.
                "registration_token": make_registration_token(user),
            },
            status=status.HTTP_200_OK,
        )

    if otp_type == OTPCode.OTP_TYPE_LOGIN:
        tokens = get_tokens_for_user(user)
        return Response(
            {
                "message": "Login successful.",
                "tokens": tokens,
                "user": UserProfileSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )

    return Response(
        {"message": "OTP verified successfully."},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([AuthRateThrottle])
def register(request):
    serializer = UserRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    username = serializer.validated_data.get("username", "").strip()
    phone = serializer.validated_data.get("phone", "").strip()
    password = serializer.validated_data["password"]
    first_name = serializer.validated_data.get("first_name", "")
    last_name = serializer.validated_data.get("last_name", "")
    email = serializer.validated_data.get("email", "")

    phone_val = phone or username
    username_val = username or phone

    matches = list(
        User.objects.filter(
            Q(phone__iexact=phone_val) | Q(username__iexact=phone_val)
            | Q(phone__iexact=username_val) | Q(username__iexact=username_val)
        )
    )
    if any(u.has_usable_password() for u in matches):
        return Response(
            {"error": "User already registered. Please login."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # What is left are placeholders made by "send me a code" (a phone and no password yet).
    existing_user = next((u for u in matches if u.phone == phone_val), None)
    if len(matches) > (1 if existing_user else 0):
        # The chosen username is a phone number someone else is registering with.
        return Response(
            {"error": "This username is not available."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Finishing an OTP registration sets the password of the placeholder, so the caller must
    # prove they are the one who received the code: knowing the phone number is not enough.
    if existing_user and not (
        existing_user.is_verified
        and registration_token_matches(serializer.validated_data.get("registration_token", ""), existing_user)
    ):
        return Response(
            {"error": "Please verify your phone number before registering."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if existing_user:
        existing_user.set_password(password)
        if first_name:
            existing_user.first_name = first_name
        if last_name:
            existing_user.last_name = last_name
        if email:
            existing_user.email = email
        if username and not existing_user.username:
            existing_user.username = username
        existing_user.is_verified = True
        existing_user.save()
        tokens = get_tokens_for_user(existing_user)
        return Response(
            {
                "message": "Registration successful.",
                "tokens": tokens,
                "user": UserProfileSerializer(existing_user).data,
            },
            status=status.HTTP_201_CREATED,
        )

    user = User.objects.create_user(
        phone=phone_val,
        username=username_val,
        password=password,
        first_name=first_name,
        last_name=last_name,
        email=email,
        # Registered without an OTP: the phone number has not been proven.
        is_verified=False,
    )
    tokens = get_tokens_for_user(user)
    return Response(
        {
            "message": "Registration successful.",
            "tokens": tokens,
            "user": UserProfileSerializer(user).data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([OTPRateThrottle])
@transaction.atomic
def reset_password(request):
    serializer = PasswordResetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    phone = serializer.validated_data["phone"]
    code = serializer.validated_data["code"]

    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        return error_response("user_not_found", "No user found with this phone number.", status.HTTP_404_NOT_FOUND)

    # Before the code is looked at: a refused password must not use up the code or count as
    # a wrong guess, so the customer can simply type a better one.
    check_password_rules(serializer.validated_data["new_password"], user=user)

    otp, error = OTPCode.check_code(user, OTPCode.OTP_TYPE_RESET_PASSWORD, code)
    if error:
        return otp_error_response(error)

    otp.mark_used()
    user.set_password(serializer.validated_data["new_password"])
    user.save()

    return Response(
        {"message": "Password reset successful. You can now login."},
        status=status.HTTP_200_OK,
    )


@api_view(["GET", "PUT", "PATCH"])
@permission_classes([permissions.IsAuthenticated])
def profile(request):
    user = request.user

    if request.method == "GET":
        return Response(UserProfileSerializer(user).data, status=status.HTTP_200_OK)

    serializer = UserProfileSerializer(user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([AuthRateThrottle])
def login_with_password(request):
    serializer = UserLoginSerializer(data=request.data)
    validate_coded(serializer)

    user = serializer.validated_data["user"]
    tokens = get_tokens_for_user(user)
    return Response(
        {
            "message": "Login successful.",
            "tokens": tokens,
            "user": UserProfileSerializer(user).data,
        },
        status=status.HTTP_200_OK,
    )
