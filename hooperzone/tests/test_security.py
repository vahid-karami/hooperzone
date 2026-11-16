"""Tests for security fixes: each one fails on the code as it was before the fix."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def paid_order(db):
    from orders.models import Order

    owner = User.objects.create_user(phone="09125550001", password="securepass123")
    return Order.objects.create(
        user=owner, order_number="ORD-PAID0001", shipping_address="Valiasr St, no. 12", shipping_city="Tehran",
        shipping_zip="1234567890", shipping_phone="09125550001", subtotal=100, total=100,
        payment_status=Order.PAYMENT_STATUS_PAID, status=Order.STATUS_CONFIRMED,
        payment_gateway="zarinpal", payment_authority="A0000000000000000000000000000012345", payment_ref_id="777",
    )


@pytest.mark.django_db
class TestPaymentVerifyPrivacy:
    """The verify endpoint is public: an order number alone must not reveal the order."""

    url = reverse("orders:order-pay-verify")

    def test_paid_order_is_not_shown_without_its_authority(self, paid_order):
        for authority in ("guess", "ZP-MOCK-x"):
            res = APIClient().post(self.url, {"order_number": paid_order.order_number, "authority": authority})
            assert res.status_code == 400
            assert "order" not in res.data
            assert "Valiasr" not in str(res.data)

    def test_paid_order_is_shown_again_with_its_authority(self, paid_order):
        res = APIClient().post(
            self.url, {"order_number": paid_order.order_number, "authority": paid_order.payment_authority}
        )
        assert res.status_code == 200
        assert res.data["order"]["order_number"] == paid_order.order_number
        assert res.data["ref_id"] == "777"

    def test_unknown_order_looks_like_a_wrong_authority(self, paid_order):
        unknown = APIClient().post(self.url, {"order_number": "ORD-NOPE0000", "authority": "guess"})
        wrong = APIClient().post(self.url, {"order_number": paid_order.order_number, "authority": "guess"})
        assert (unknown.status_code, unknown.data) == (wrong.status_code, wrong.data)


class TestCsvFormulaInjection:
    def test_formula_cells_are_written_as_text(self):
        from hooperzone.csv_export import csv_response

        rows = [["=HYPERLINK(\"http://evil\")", "+989120000000", "-1+1", "@SUM(A1)", "Ali", 1500, -3]]
        lines = csv_response("x", ["a"], rows).content.decode("utf-8").splitlines()
        assert lines[1] == "\"'=HYPERLINK(\"\"http://evil\"\")\",'+989120000000,'-1+1,'@SUM(A1),Ali,1500,-3"

    @pytest.mark.django_db
    def test_order_export_neutralises_a_customer_address(self, paid_order):
        paid_order.shipping_address = "=cmd|' /C calc'!A0"
        paid_order.save()
        staff = User.objects.create_superuser(phone="09125550002", password="securepass123")
        client = APIClient()
        client.force_authenticate(staff)
        body = client.get(reverse("orders:admin-order-export")).content.decode("utf-8")
        assert "'=cmd|" in body and ",=cmd|" not in body


@pytest.mark.django_db
class TestOtpGuessLimit:
    """A code dies after a few wrong guesses, whatever IP they come from."""

    def _code(self, user, otp_type):
        from accounts.models import OTPCode

        return OTPCode.objects.create(user=user, otp_type=otp_type)

    def _wrong(self, code):
        return "000000" if code != "000000" else "111111"

    def test_login_code_is_cancelled_after_five_wrong_guesses(self):
        from accounts.models import OTPCode

        user = User.objects.create_user(phone="09125550003", password="securepass123")
        otp = self._code(user, "login")
        url = reverse("accounts:otp-verify")
        payload = {"phone": user.phone, "otp_type": "login"}
        for _ in range(OTPCode.MAX_FAILED_ATTEMPTS):
            assert APIClient().post(url, {**payload, "code": self._wrong(otp.code)}).status_code == 400
        # The right code no longer works: the attacker's sixth try can't be the lucky one.
        res = APIClient().post(url, {**payload, "code": otp.code})
        assert res.status_code == 400 and "tokens" not in res.data
        otp.refresh_from_db()
        assert otp.is_used and otp.failed_attempts == OTPCode.MAX_FAILED_ATTEMPTS

    def test_a_few_typos_do_not_cancel_the_code(self):
        user = User.objects.create_user(phone="09125550004", password="securepass123")
        otp = self._code(user, "login")
        url = reverse("accounts:otp-verify")
        payload = {"phone": user.phone, "otp_type": "login"}
        for _ in range(2):
            assert APIClient().post(url, {**payload, "code": self._wrong(otp.code)}).status_code == 400
        assert "tokens" in APIClient().post(url, {**payload, "code": otp.code}).data

    def test_password_reset_code_has_the_same_limit(self):
        from accounts.models import OTPCode

        user = User.objects.create_user(phone="09125550005", password="securepass123")
        otp = self._code(user, "reset_password")
        url = reverse("accounts:password-reset")
        payload = {"phone": user.phone, "new_password": "attackerpass1"}
        for _ in range(OTPCode.MAX_FAILED_ATTEMPTS):
            assert APIClient().post(url, {**payload, "code": self._wrong(otp.code)}).status_code == 400
        assert APIClient().post(url, {**payload, "code": otp.code}).status_code == 400
        user.refresh_from_db()
        assert user.check_password("securepass123")

    def test_wrong_guess_of_another_type_does_not_count(self):
        user = User.objects.create_user(phone="09125550006", password="securepass123")
        otp = self._code(user, "login")
        res = APIClient().post(
            reverse("accounts:otp-verify"), {"phone": user.phone, "otp_type": "reset_password", "code": "000000"}
        )
        assert res.status_code == 400
        otp.refresh_from_db()
        assert otp.failed_attempts == 0
