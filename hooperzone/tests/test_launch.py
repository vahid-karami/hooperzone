"""Checks for things that must hold before the shop takes real money."""
from datetime import timedelta
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from cart.models import Cart, CartItem
from orders import payments
from orders.models import Order, OrderItem, ShopSettings
from orders.services import cancel_unpaid_orders
from products.models import Category, Product

User = get_user_model()

SHIPPING = {
    "shipping_address": "Azadi St", "shipping_city": "Tehran",
    "shipping_zip": "1234567890", "shipping_phone": "09127777777",
}


@pytest.fixture
def product(db):
    cat = Category.objects.create(name="Knee", slug="knee")
    return Product.objects.create(category=cat, name="Brace", slug="brace", description="d", price=1_250_000, stock=5)


@pytest.fixture
def shopper(product):
    user = User.objects.create_user(phone="09127777777", password="securepass123")
    CartItem.objects.create(cart=Cart.objects.create(user=user), product=product, quantity=2)
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def order(product):
    user = User.objects.create_user(phone="09128888888", password="securepass123")
    order = Order.objects.create(
        user=user, order_number="ORD-LAUNCH01", shipping_address="x", shipping_city="Tehran",
        shipping_zip="1234567890", shipping_phone="09128888888", subtotal=1_250_000, total=1_310_000,
    )
    OrderItem.objects.create(order=order, product=product, product_name="Brace", product_price=1_250_000, quantity=1)
    return order


@pytest.mark.django_db
class TestShipping:
    def test_methods_use_fees_from_shop_settings(self):
        shop = ShopSettings.load()
        shop.shipping_tipax = 200_000
        shop.save()
        res = APIClient().get(reverse("orders:shipping-methods"))
        assert res.status_code == 200
        fees = {m["code"]: m["fee"] for m in res.data}
        assert fees == {"post": shop.shipping_post, "pishtaz": shop.shipping_pishtaz, "tipax": 200_000}

    @pytest.mark.parametrize("method", ["post", "pishtaz", "tipax"])
    def test_order_total_includes_chosen_method_fee(self, shopper, method):
        fee = ShopSettings.load().shipping_fee(method)
        res = shopper.post(reverse("orders:order-create"), {**SHIPPING, "shipping_method": method})
        assert res.status_code == status.HTTP_201_CREATED, res.data
        assert res.data["shipping_method"] == method
        assert float(res.data["shipping_cost"]) == fee
        assert float(res.data["total"]) == 2_500_000 + fee

    def test_unknown_method_is_rejected(self, shopper):
        res = shopper.post(reverse("orders:order-create"), {**SHIPPING, "shipping_method": "camel"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_shop_info_is_public(self):
        res = APIClient().get(reverse("orders:shop-info"))
        assert res.status_code == 200
        assert len(res.data["shipping_methods"]) == 3


@pytest.mark.django_db
class TestZarinPal:
    def test_amount_is_sent_in_toman(self, order, settings):
        settings.PAYMENT_SANDBOX = False
        settings.ZARINPAL_MERCHANT_ID = "real-merchant"
        with mock.patch.object(payments, "_post_json", return_value={"data": {"code": 100, "authority": "A0001"}}) as post:
            result = payments.ZarinPalGateway(sandbox=False).request_payment(order, "https://hooperzone.ir/payment/result")
        url, payload = post.call_args.args
        assert url == "https://payment.zarinpal.com/pg/v4/payment/request.json"
        assert payload["amount"] == 1_310_000
        assert payload["currency"] == "IRT"
        assert payload["merchant_id"] == "real-merchant"
        assert result["payment_url"] == "https://payment.zarinpal.com/pg/StartPay/A0001"

    def test_live_mode_never_falls_back_to_mock(self, order, settings):
        settings.PAYMENT_MOCK_FALLBACK = False
        with mock.patch.object(payments, "_post_json", side_effect=OSError("down")):
            with pytest.raises(payments.PaymentGatewayError):
                payments.ZarinPalGateway(sandbox=True).request_payment(order, "https://hooperzone.ir/x")

    def test_mock_authority_rejected_without_mock_fallback(self, order, settings):
        settings.PAYMENT_MOCK_FALLBACK = False
        result = payments.ZarinPalGateway(sandbox=True).verify_payment(order, "ZP-MOCK-abc")
        assert result["success"] is False

    def test_missing_merchant_id_fails_cleanly(self, order, settings):
        settings.PAYMENT_MOCK_FALLBACK = False
        settings.ZARINPAL_MERCHANT_ID = ""
        with pytest.raises(payments.PaymentGatewayError):
            payments.ZarinPalGateway(sandbox=False).request_payment(order, "https://hooperzone.ir/x")

    def test_verify_stores_ref_id(self, order, settings):
        order.payment_gateway, order.payment_authority = "zarinpal", "A0001"
        order.save()
        reply = {"data": {"code": 100, "ref_id": 987654, "card_pan": "6037**1234"}}
        with mock.patch.object(payments, "_post_json", return_value=reply) as post:
            res = APIClient().get(
                reverse("orders:order-pay-verify"),
                {"order_number": order.order_number, "Authority": "A0001", "Status": "OK"},
            )
        assert res.status_code == 200, res.data
        assert post.call_args.args[1]["amount"] == 1_310_000
        order.refresh_from_db()
        assert order.payment_status == Order.PAYMENT_STATUS_PAID
        assert order.payment_ref_id == "987654"
        assert order.payment_card_pan == "6037**1234"
        assert order.paid_at is not None

    def test_nok_callback_marks_failed_without_verifying(self, order):
        order.payment_gateway, order.payment_authority = "zarinpal", "A0001"
        order.save()
        with mock.patch.object(payments, "_post_json") as post:
            res = APIClient().get(
                reverse("orders:order-pay-verify"),
                {"order_number": order.order_number, "Authority": "A0001", "Status": "NOK"},
            )
        assert res.status_code == 400
        post.assert_not_called()
        order.refresh_from_db()
        assert order.payment_status == Order.PAYMENT_STATUS_FAILED


@pytest.mark.django_db
class TestSMS:
    def _reply(self, body):
        response = mock.MagicMock()
        response.read.return_value = body
        response.__enter__.return_value = response
        return response

    def test_otp_is_sent_through_smsir(self, settings):
        settings.SMSIR_API_KEY, settings.SMSIR_TEMPLATE_ID = "key", "123456"
        settings.OTP_RETURN_IN_RESPONSE = False
        reply = self._reply(b'{"status": 1, "message": "ok"}')
        with mock.patch("accounts.sms.urllib.request.urlopen", return_value=reply) as urlopen:
            res = APIClient().post(reverse("accounts:otp-send"), {"phone": "09121111111", "otp_type": "register"})
        assert res.status_code == 200
        assert "otp" not in res.data
        request = urlopen.call_args.args[0]
        assert request.full_url == "https://api.sms.ir/v1/send/verify"
        assert request.get_header("X-api-key") == "key"
        import json

        body = json.loads(request.data)
        assert body["mobile"] == "09121111111"
        assert body["templateId"] == 123456
        assert body["parameters"][0]["name"] == "CODE"
        assert len(body["parameters"][0]["value"]) == 6

    def test_sms_failure_returns_503_and_burns_code(self, settings):
        from accounts.models import OTPCode

        settings.SMSIR_API_KEY, settings.SMSIR_TEMPLATE_ID = "key", "123456"
        with mock.patch("accounts.sms.urllib.request.urlopen", side_effect=OSError("down")):
            res = APIClient().post(reverse("accounts:otp-send"), {"phone": "09121111112", "otp_type": "register"})
        assert res.status_code == 503
        assert not OTPCode.objects.filter(user__phone="09121111112", is_used=False).exists()


@pytest.mark.django_db
class TestAuthHardening:
    def test_password_login_is_throttled_per_client_ip(self, monkeypatch):
        from rest_framework.throttling import SimpleRateThrottle

        monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {"auth": "3/min", "otp": "10/min"})
        url = reverse("accounts:login")
        attacker = APIClient(HTTP_CF_CONNECTING_IP="5.5.5.5")
        codes = [attacker.post(url, {"username": "x", "password": "wrong"}).status_code for _ in range(4)]
        assert codes[-1] == status.HTTP_429_TOO_MANY_REQUESTS
        # Another visitor behind the same Cloudflare edge is not blocked.
        other = APIClient(HTTP_CF_CONNECTING_IP="6.6.6.6")
        assert other.post(url, {"username": "x", "password": "wrong"}).status_code != 429

    def test_direct_registration_does_not_mark_phone_verified(self):
        res = APIClient().post(reverse("accounts:register"), {"phone": "09123334444", "password": "securepass123"})
        assert res.status_code == 201
        assert User.objects.get(phone="09123334444").is_verified is False


@pytest.mark.django_db
class TestUnpaidOrders:
    def test_old_unpaid_orders_are_cancelled_and_restocked(self, order, product):
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(hours=2))
        assert cancel_unpaid_orders(60) == 1
        order.refresh_from_db()
        product.refresh_from_db()
        assert order.status == Order.STATUS_CANCELLED
        assert product.stock == 6

    def test_recent_and_paid_orders_are_kept(self, order, product):
        assert cancel_unpaid_orders(60) == 0
        Order.objects.filter(pk=order.pk).update(
            created_at=timezone.now() - timedelta(hours=2), payment_status=Order.PAYMENT_STATUS_PAID
        )
        assert cancel_unpaid_orders(60) == 0

    def test_zero_timeout_disables_the_sweep(self, order):
        Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(days=5))
        assert cancel_unpaid_orders(0) == 0


@pytest.mark.django_db
def test_backup_db_copies_sqlite(tmp_path):
    import sqlite3

    db = tmp_path / "db.sqlite3"
    with sqlite3.connect(db) as conn:
        conn.execute("create table t (x int)")
    call_command("backup_db", source=str(db))
    assert len(list((tmp_path / "backups").glob("db-*.sqlite3"))) == 1


@pytest.mark.django_db
def test_otp_fails_clearly_when_sms_is_required_but_not_configured(settings):
    settings.SMS_REQUIRED = True
    settings.SMSIR_API_KEY = ""
    res = APIClient().post(reverse("accounts:otp-send"), {"phone": "09121111113", "otp_type": "register"})
    assert res.status_code == 503
