"""Regression tests for bugs fixed after the initial import."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import OTPCode

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestOTPSecurity:
    def test_otp_not_leaked_when_disabled(self, api_client, settings):
        settings.OTP_RETURN_IN_RESPONSE = False
        victim = User.objects.create_user(phone="09120000001", password="securepass123")
        res = api_client.post(reverse("accounts:otp-send"), {"phone": victim.phone, "otp_type": "login"})
        assert res.status_code == status.HTTP_200_OK
        assert "otp" not in res.data

    def test_otp_code_is_six_digits(self):
        for _ in range(200):
            code = OTPCode.generate_code()
            assert len(code) == 6 and code.isdigit()

    def test_otp_verify_is_throttled(self, api_client, monkeypatch):
        from rest_framework.throttling import SimpleRateThrottle

        monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {"otp": "3/min"})
        user = User.objects.create_user(phone="09120000002", password="securepass123")
        url = reverse("accounts:otp-verify")
        codes = [
            api_client.post(url, {"phone": user.phone, "code": "000000", "otp_type": "login"}).status_code
            for _ in range(4)
        ]
        assert codes[-1] == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.django_db
class TestOTPRegistrationFlow:
    def _send_and_verify(self, api_client, phone):
        api_client.post(reverse("accounts:otp-send"), {"phone": phone, "otp_type": "register"})
        otp = OTPCode.objects.filter(user__phone=phone, otp_type="register").latest("created_at")
        return api_client.post(
            reverse("accounts:otp-verify"), {"phone": phone, "code": otp.code, "otp_type": "register"}
        )

    def test_register_after_otp_verification(self, api_client):
        phone = "09121111111"
        assert self._send_and_verify(api_client, phone).status_code == status.HTTP_200_OK
        res = api_client.post(
            reverse("accounts:register"), {"phone": phone, "username": phone, "password": "securepass123"}
        )
        assert res.status_code == status.HTTP_201_CREATED, res.data

    def test_register_otp_can_be_resent(self, api_client):
        url = reverse("accounts:otp-send")
        assert api_client.post(url, {"phone": "09122222222", "otp_type": "register"}).status_code == 200
        assert api_client.post(url, {"phone": "09122222222", "otp_type": "register"}).status_code == 200

    def test_cannot_claim_unverified_phone_without_otp(self, api_client):
        phone = "09123333333"
        api_client.post(reverse("accounts:otp-send"), {"phone": phone, "otp_type": "register"})
        res = api_client.post(reverse("accounts:register"), {"phone": phone, "password": "attackerpass1"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert not User.objects.get(phone=phone).has_usable_password()

    def test_reset_otp_for_unknown_phone_does_not_create_user(self, api_client):
        res = api_client.post(reverse("accounts:otp-send"), {"phone": "09124444444", "otp_type": "reset_password"})
        assert res.status_code == status.HTTP_404_NOT_FOUND
        assert not User.objects.filter(phone="09124444444").exists()


@pytest.fixture
def order(db):
    from orders.models import Order

    owner = User.objects.create_user(phone="09125555555", password="securepass123")
    return Order.objects.create(
        user=owner, order_number="ORD-TEST0001", shipping_address="x", shipping_city="Tehran",
        shipping_zip="1234567890", shipping_phone="09125555555", subtotal=100, total=100,
    )


@pytest.mark.django_db
class TestPaymentVerification:
    def test_forged_mock_authority_does_not_mark_order_paid(self, api_client, order):
        from orders.models import Order

        res = api_client.post(
            reverse("orders:order-pay-verify"),
            {"order_number": order.order_number, "authority": "ZP-MOCK-forged", "gateway": "zarinpal"},
        )
        order.refresh_from_db()
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert order.payment_status != Order.PAYMENT_STATUS_PAID

    def test_idpay_verification_does_not_crash(self, order):
        from orders.models import Order

        client = APIClient()
        client.force_authenticate(order.user)
        init = client.post(
            reverse("orders:order-pay-initiate", kwargs={"order_number": order.order_number}), {"gateway": "idpay"}
        )
        assert init.status_code == status.HTTP_200_OK
        res = APIClient().post(
            reverse("orders:order-pay-verify"),
            {"order_number": order.order_number, "id": init.data["id"], "gateway": "idpay"},
        )
        assert res.status_code == status.HTTP_200_OK, res.data
        order.refresh_from_db()
        assert order.payment_status == Order.PAYMENT_STATUS_PAID

    def test_cannot_pay_cancelled_order(self, order):
        from orders.models import Order

        order.status = Order.STATUS_CANCELLED
        order.save()
        client = APIClient()
        client.force_authenticate(order.user)
        res = client.post(reverse("orders:order-pay-initiate", kwargs={"order_number": order.order_number}))
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.fixture
def shopper_with_cart(db):
    from cart.models import Cart, CartItem
    from products.models import Category, Product

    cat = Category.objects.create(name="Knee", slug="knee")
    product = Product.objects.create(category=cat, name="Brace", slug="brace", description="d", price=50, stock=5)
    user = User.objects.create_user(phone="09126666666", password="securepass123")
    CartItem.objects.create(cart=Cart.objects.create(user=user), product=product, quantity=2)
    client = APIClient()
    client.force_authenticate(user)
    return client, product


SHIPPING = {
    "shipping_address": "Azadi St", "shipping_city": "Tehran",
    "shipping_zip": "1234567890", "shipping_phone": "09126666666",
}


@pytest.mark.django_db
class TestOrderCreation:
    def test_cannot_order_deactivated_product(self, shopper_with_cart):
        client, product = shopper_with_cart
        product.is_active = False
        product.save()
        res = client.post(reverse("orders:order-create"), SHIPPING)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        product.refresh_from_db()
        assert product.stock == 5

    def test_create_then_cancel_restores_stock(self, shopper_with_cart):
        client, product = shopper_with_cart
        res = client.post(reverse("orders:order-create"), SHIPPING)
        assert res.status_code == status.HTTP_201_CREATED
        product.refresh_from_db()
        assert product.stock == 3
        client.post(reverse("orders:order-cancel", kwargs={"order_number": res.data["order_number"]}))
        product.refresh_from_db()
        assert product.stock == 5


@pytest.mark.django_db
class TestCartQuantityValidation:
    @pytest.mark.parametrize("quantity", ["abc", -3, 0])
    def test_add_rejects_invalid_quantity(self, shopper_with_cart, quantity):
        from cart.models import CartItem

        client, product = shopper_with_cart
        res = client.post(reverse("cart:cart-add"), {"product_id": product.id, "quantity": quantity}, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert CartItem.objects.get(product=product).quantity == 2

    def test_update_rejects_non_numeric_quantity(self, shopper_with_cart):
        from cart.models import CartItem

        client, product = shopper_with_cart
        item = CartItem.objects.get(product=product)
        res = client.patch(reverse("cart:cart-update"), {"item_id": item.id, "quantity": "x"}, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.parametrize(
        "method,name,payload",
        [
            ("post", "cart:cart-add", {"product_id": "abc"}),
            ("patch", "cart:cart-update", {"item_id": "abc", "quantity": 1}),
            ("delete", "cart:cart-remove", {"item_id": "abc"}),
            ("post", "favorites:favorite-add", {"product_id": "abc"}),
            ("delete", "favorites:favorite-remove", {"product_id": "abc"}),
        ],
    )
    def test_non_numeric_ids_return_404(self, shopper_with_cart, method, name, payload):
        client, _ = shopper_with_cart
        res = getattr(client, method)(reverse(name), payload, format="json")
        assert res.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestAdminProductCreate:
    def test_admin_can_create_multiple_products(self):
        from products.models import Category

        admin = User.objects.create_superuser(phone="09127777777", password="securepass123")
        cat = Category.objects.create(name="Knee", slug="knee")
        client = APIClient()
        client.force_authenticate(admin)
        url = reverse("products:admin-product-list")
        slugs = []
        for name in ["Knee Brace", "Knee Brace", "زانوبند"]:
            res = client.post(url, {"name": name, "description": "d", "category": cat.id, "price": "10"})
            assert res.status_code == status.HTTP_201_CREATED, res.data
            slugs.append(res.data["slug"])
        assert len(set(slugs)) == 3 and all(slugs)


@pytest.mark.django_db
def test_public_reviews_do_not_expose_personal_data(api_client):
    from products.models import Category, Product
    from reviews.models import Review

    cat = Category.objects.create(name="Knee", slug="knee")
    product = Product.objects.create(category=cat, name="Brace", slug="brace", description="d", price=50)
    reviewer = User.objects.create_user(
        phone="09128888888", password="securepass123", email="a@b.c", first_name="Sara",
        address="Secret St 1", postal_code="1234567890",
    )
    Review.objects.create(user=reviewer, product=product, rating=5, title="t", comment="c")
    res = api_client.get(reverse("reviews:product-reviews", kwargs={"product_slug": "brace"}))
    body = str(res.data)
    for secret in ["09128888888", "a@b.c", "Secret St 1", "1234567890"]:
        assert secret not in body
    assert res.data[0]["user"]["first_name"] == "Sara"


@pytest.mark.django_db
class TestBulkPriceUpdate:
    @pytest.fixture
    def admin_client(self):
        admin = User.objects.create_superuser(phone="09129999999", password="securepass123")
        client = APIClient()
        client.force_authenticate(admin)
        return client

    @pytest.fixture
    def products(self):
        from products.models import Category, Product

        cat = Category.objects.create(name="Knee", slug="knee")
        return [
            Product.objects.create(category=cat, name="A", slug="a", description="d", price=890000),
            Product.objects.create(category=cat, name="B", slug="b", description="d", price="49.99"),
        ]

    url = "/api/products/admin/products/bulk_price_update/"

    @pytest.mark.parametrize("percentage", [-100, -150, "nan", [1], {"a": 1}])
    def test_rejects_invalid_percentage(self, admin_client, products, percentage):
        res = admin_client.post(self.url, {"percentage": percentage}, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_rounds_without_zeroing_small_prices(self, admin_client, products):
        from decimal import Decimal

        res = admin_client.post(self.url, {"percentage": 10}, format="json")
        assert res.status_code == status.HTTP_200_OK
        big, small = (p.__class__.objects.get(pk=p.pk) for p in products)
        assert big.price == Decimal("979000")
        assert small.price == Decimal("54.99")


@pytest.mark.django_db
def test_adding_existing_favorite_returns_list(shopper_with_cart):
    client, product = shopper_with_cart
    url = reverse("favorites:favorite-add")
    client.post(url, {"product_id": product.id}, format="json")
    res = client.post(url, {"product_id": product.id}, format="json")
    assert res.status_code == status.HTTP_200_OK
    assert res.data["total_items"] == 1


@pytest.mark.django_db
def test_product_list_on_sale_and_featured_filters(api_client):
    from products.models import Category, Product

    cat = Category.objects.create(name="Knee", slug="knee")
    Product.objects.create(category=cat, name="A", slug="a", description="d", price=100, discount_price=80)
    Product.objects.create(category=cat, name="B", slug="b", description="d", price=100, is_featured=True)
    url = reverse("products:product-list")
    assert [p["slug"] for p in api_client.get(url, {"on_sale": "true"}).data["results"]] == ["a"]
    assert [p["slug"] for p in api_client.get(url, {"is_featured": "true"}).data["results"]] == ["b"]


@pytest.mark.django_db
def test_profile_exposes_read_only_is_staff():
    user = User.objects.create_user(phone="09121212121", password="securepass123")
    client = APIClient()
    client.force_authenticate(user)
    res = client.patch(reverse("accounts:profile"), {"is_staff": True}, format="json")
    assert res.data["is_staff"] is False
    user.refresh_from_db()
    assert user.is_staff is False


@pytest.mark.django_db
class TestPaymentCallback:
    def _client(self, order):
        client = APIClient()
        client.force_authenticate(order.user)
        return client

    def test_foreign_callback_url_is_rejected(self, order):
        res = self._client(order).post(
            reverse("orders:order-pay-initiate", kwargs={"order_number": order.order_number}),
            {"gateway": "zarinpal", "callback_url": "https://evil.example/steal"},
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_sandbox_payment_returns_to_storefront_result_page(self, order, settings):
        settings.PAYMENT_SANDBOX = True
        callback = "http://localhost:5173/payment/result?order_number=%s&gateway=zarinpal" % order.order_number
        res = self._client(order).post(
            reverse("orders:order-pay-initiate", kwargs={"order_number": order.order_number}),
            {"gateway": "zarinpal", "callback_url": callback},
        )
        assert res.status_code == status.HTTP_200_OK, res.data
        assert res.data["payment_url"].startswith(callback + "&Authority=ZP-MOCK-")


@pytest.mark.django_db
class TestPersianDigits:
    def test_login_with_persian_digit_phone(self, api_client):
        User.objects.create_user(phone="09121234567", password="securepass123")
        res = api_client.post(reverse("accounts:login"), {"phone": "۰۹۱۲۱۲۳۴۵۶۷", "password": "securepass123"})
        assert res.status_code == status.HTTP_200_OK, res.data

    def test_register_with_persian_digits_cannot_duplicate_phone(self, api_client):
        User.objects.create_user(phone="09121234567", password="securepass123")
        res = api_client.post(reverse("accounts:register"), {"phone": "۰۹۱۲۱۲۳۴۵۶۷", "password": "anotherpass123"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert User.objects.count() == 1

    def test_profile_phone_is_normalized_and_unique(self):
        User.objects.create_user(phone="09120000009", password="securepass123")
        me = User.objects.create_user(phone="09120000008", password="securepass123")
        client = APIClient()
        client.force_authenticate(me)
        dup = client.patch(reverse("accounts:profile"), {"phone": "۰۹۱۲۰۰۰۰۰۰۹"}, format="json")
        assert dup.status_code == status.HTTP_400_BAD_REQUEST
        ok = client.patch(reverse("accounts:profile"), {"phone": "۰۹۱۲۰۰۰۰۰۰۷"}, format="json")
        assert ok.data["phone"] == "09120000007"

    def test_order_shipping_fields_are_normalized(self, shopper_with_cart):
        client, _ = shopper_with_cart
        data = {**SHIPPING, "shipping_zip": "۱۲۳۴۵۶۷۸۹۰", "shipping_phone": "۰۹۱۲۶۶۶۶۶۶۶"}
        res = client.post(reverse("orders:order-create"), data)
        assert res.status_code == status.HTTP_201_CREATED
        assert (res.data["shipping_zip"], res.data["shipping_phone"]) == ("1234567890", "09126666666")
