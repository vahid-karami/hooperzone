"""Auth errors carry a stable `code` next to the English text, so the storefront can translate them."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import OTPCode

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(phone="09128880001", password="securepass123")


def _reset(user, code, password="blue-Kettle-41"):
    return APIClient().post(
        reverse("accounts:password-reset"), {"phone": user.phone, "code": code, "new_password": password}
    )


def _wrong(code):
    return "000000" if code != "000000" else "111111"


@pytest.mark.django_db
class TestOtpSendCodes:
    url = reverse("accounts:otp-send")

    def test_unknown_phone(self):
        res = APIClient().post(self.url, {"phone": "09128880002", "otp_type": "reset_password"})
        assert (res.status_code, res.data["code"]) == (404, "user_not_found") and res.data["error"]

    def test_phone_already_registered(self, user):
        res = APIClient().post(self.url, {"phone": user.phone, "otp_type": "register"})
        assert (res.status_code, res.data["code"]) == (400, "phone_exists")

    def test_sms_provider_down(self, user, monkeypatch):
        from accounts import views
        from accounts.sms import SMSError

        def fail(phone, code):
            raise SMSError("down")

        monkeypatch.setattr(views, "send_otp_sms", fail)
        res = APIClient().post(self.url, {"phone": user.phone, "otp_type": "reset_password"})
        assert (res.status_code, res.data["code"]) == (503, "sms_failed")


@pytest.mark.django_db
class TestResetCodes:
    def test_no_code_was_requested(self, user):
        assert _reset(user, "123456").data["code"] == "otp_invalid"

    def test_wrong_then_locked(self, user):
        otp = OTPCode.objects.create(user=user, otp_type="reset_password")
        codes = [_reset(user, _wrong(otp.code)).data["code"] for _ in range(OTPCode.MAX_FAILED_ATTEMPTS)]
        assert codes == ["otp_invalid"] * (OTPCode.MAX_FAILED_ATTEMPTS - 1) + ["otp_locked"]

    def test_expired(self, user):
        from datetime import timedelta

        from django.utils import timezone

        otp = OTPCode.objects.create(user=user, otp_type="reset_password")
        OTPCode.objects.filter(pk=otp.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        res = _reset(user, otp.code)
        assert (res.status_code, res.data["code"]) == (400, "otp_expired")

    def test_unknown_phone(self, db):
        res = APIClient().post(
            reverse("accounts:password-reset"), {"phone": "09128880003", "code": "123456", "new_password": "blue-Kettle-41"}
        )
        assert (res.status_code, res.data["code"]) == (404, "user_not_found")

    def test_success_then_login_with_the_new_password(self, user):
        otp = OTPCode.objects.create(user=user, otp_type="reset_password")
        assert _reset(user, otp.code).status_code == 200
        login = APIClient().post(reverse("accounts:login"), {"phone": user.phone, "password": "blue-Kettle-41"})
        assert login.status_code == 200 and "tokens" in login.data
        # The code can't be used a second time.
        assert _reset(user, otp.code, "other-Kettle-42").data["code"] == "otp_invalid"

    def test_login_code_does_not_reset_a_password(self, user):
        otp = OTPCode.objects.create(user=user, otp_type="login")
        assert _reset(user, otp.code).data["code"] == "otp_invalid"
        user.refresh_from_db()
        assert user.check_password("securepass123")
