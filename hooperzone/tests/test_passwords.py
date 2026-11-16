"""Customer passwords follow Django's password rules, not just a minimum length."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import serializers
from rest_framework.test import APIClient

from accounts.passwords import check_password_rules

User = get_user_model()

WEAK = [
    ("12345678", "password_entirely_numeric"),
    ("09121234567", "password_entirely_numeric"),
    ("password", "password_too_common"),
    ("qwertyuiop", "password_too_common"),
    ("short1a", "password_too_short"),
]


class TestRules:
    @pytest.mark.parametrize("password, code", WEAK)
    def test_weak_passwords_are_refused_with_their_rule_code(self, password, code):
        with pytest.raises(serializers.ValidationError) as error:
            check_password_rules(password)
        assert code in error.value.detail["password_codes"]
        assert len(error.value.detail["password"]) == len(error.value.detail["password_codes"])

    def test_password_that_copies_the_username_or_name_is_refused(self):
        for attrs in ({"username": "sara_ahmadi"}, {"first_name": "Sara", "last_name": "ahmadi99x"}):
            with pytest.raises(serializers.ValidationError) as error:
                check_password_rules("ahmadi99x" if "last_name" in attrs else "sara_ahmadi", **attrs)
            assert error.value.detail["password_codes"] == ["password_too_similar"]

    @pytest.mark.parametrize("password", ["securepass123", "کلمه‌عبور۱۲۳", "blue-Kettle-41", "zanoo band 7"])
    def test_ordinary_passwords_pass(self, password):
        check_password_rules(password, username="09121234567", first_name="Sara")


@pytest.mark.django_db
class TestSignUp:
    url = reverse("accounts:register")

    @pytest.mark.parametrize("password, code", WEAK[:4])
    def test_weak_password_does_not_create_an_account(self, password, code):
        res = APIClient().post(self.url, {"phone": "09127770001", "password": password})
        assert res.status_code == 400
        assert code in res.data["password_codes"] and res.data["password"]
        assert not User.objects.filter(phone="09127770001").exists()

    def test_password_equal_to_the_username_is_refused(self):
        res = APIClient().post(self.url, {"username": "sara_ahmadi", "password": "sara_ahmadi"})
        assert res.status_code == 400 and res.data["password_codes"] == ["password_too_similar"]

    def test_good_password_registers(self):
        res = APIClient().post(self.url, {"phone": "09127770002", "password": "blue-Kettle-41", "first_name": "Sara"})
        assert res.status_code == 201, res.data
        assert User.objects.get(phone="09127770002").check_password("blue-Kettle-41")

    def test_weak_password_cannot_finish_an_otp_registration(self):
        from accounts.models import OTPCode

        phone = "09127770003"
        APIClient().post(reverse("accounts:otp-send"), {"phone": phone, "otp_type": "register"})
        otp = OTPCode.objects.filter(user__phone=phone).latest("created_at")
        token = APIClient().post(
            reverse("accounts:otp-verify"), {"phone": phone, "code": otp.code, "otp_type": "register"}
        ).data["registration_token"]
        payload = {"phone": phone, "username": phone, "registration_token": token}
        weak = APIClient().post(self.url, {**payload, "password": "12345678"})
        assert weak.status_code == 400 and not User.objects.get(phone=phone).has_usable_password()
        # The token still works after the customer picks a better password.
        assert APIClient().post(self.url, {**payload, "password": "blue-Kettle-41"}).status_code == 201

    def test_existing_account_is_reported_before_the_password(self):
        User.objects.create_user(phone="09127770004", password="securepass123")
        res = APIClient().post(self.url, {"phone": "09127770004", "password": "12345678"})
        assert res.status_code == 400 and "phone" in res.data and "password_codes" not in res.data


@pytest.mark.django_db
class TestPasswordReset:
    url = reverse("accounts:password-reset")

    def _user_and_code(self, phone):
        from accounts.models import OTPCode

        user = User.objects.create_user(phone=phone, username="sara_ahmadi", password="securepass123")
        return user, OTPCode.objects.create(user=user, otp_type="reset_password")

    @pytest.mark.parametrize("password, code", [
        ("12345678", "password_entirely_numeric"), ("password", "password_too_common"),
        ("sara_ahmadi", "password_too_similar"),
    ])
    def test_weak_new_password_is_refused_and_the_code_survives(self, password, code):
        user, otp = self._user_and_code("09127770010")
        payload = {"phone": user.phone, "code": otp.code}
        res = APIClient().post(self.url, {**payload, "new_password": password})
        assert res.status_code == 400 and code in res.data["password_codes"]
        otp.refresh_from_db()
        user.refresh_from_db()
        assert not otp.is_used and otp.failed_attempts == 0 and user.check_password("securepass123")
        assert APIClient().post(self.url, {**payload, "new_password": "blue-Kettle-41"}).status_code == 200
        user.refresh_from_db()
        assert user.check_password("blue-Kettle-41")
