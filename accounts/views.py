from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from hooperzone.throttling import AuthRateThrottle, IPRateThrottle

from .models import OTPCode
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


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([OTPRateThrottle])
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
        return Response(
            {"error": "A user with this phone number already exists."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if otp_type in (OTPCode.OTP_TYPE_LOGIN, OTPCode.OTP_TYPE_RESET_PASSWORD) and not is_registered:
        return Response(
            {"error": "No user found with this phone number."},
            status=status.HTTP_404_NOT_FOUND,
        )

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
        return Response(
            {"error": "Could not send the SMS. Please try again in a few minutes."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
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
def verify_otp(request):
    serializer = OTPVerifySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    phone = serializer.validated_data["phone"]
    code = serializer.validated_data["code"]
    otp_type = serializer.validated_data["otp_type"]

    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        return Response(
            {"error": "No user found with this phone number."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        otp = OTPCode.objects.filter(
            user=user,
            code=code,
            otp_type=otp_type,
            is_used=False,
        ).latest("created_at")
    except OTPCode.DoesNotExist:
        return Response(
            {"error": "Invalid OTP code."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if otp.is_expired():
        return Response(
            {"error": "OTP has expired. Please request a new one."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    otp.mark_used()

    if otp_type == OTPCode.OTP_TYPE_REGISTER:
        user.is_verified = True
        user.save(update_fields=["is_verified"])
        return Response(
            {
                "message": "Phone number verified successfully.",
                "next_step": "Please complete registration with phone and password.",
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

    identifier = username or phone
    phone_val = phone or username
    username_val = username or phone

    from django.db.models import Q

    existing_user = User.objects.filter(
        Q(phone__iexact=identifier) | Q(username__iexact=identifier)
    ).first()

    if existing_user and existing_user.has_usable_password():
        return Response(
            {"error": "User already registered. Please login."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if existing_user and not existing_user.is_verified:
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
def reset_password(request):
    serializer = PasswordResetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    phone = serializer.validated_data["phone"]
    code = serializer.validated_data["code"]

    try:
        user = User.objects.get(phone=phone)
    except User.DoesNotExist:
        return Response(
            {"error": "No user found with this phone number."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        otp = OTPCode.objects.filter(
            user=user,
            code=code,
            otp_type=OTPCode.OTP_TYPE_RESET_PASSWORD,
            is_used=False,
        ).latest("created_at")
    except OTPCode.DoesNotExist:
        return Response(
            {"error": "Invalid OTP code."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if otp.is_expired():
        return Response(
            {"error": "OTP has expired. Please request a new one."},
            status=status.HTTP_400_BAD_REQUEST,
        )

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
    serializer.is_valid(raise_exception=True)

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
