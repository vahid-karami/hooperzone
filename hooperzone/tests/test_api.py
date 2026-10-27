import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import OTPCode
from products.models import Category, Product

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return User.objects.create_user(phone="+1234567890", password="testpass123")


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def category():
    return Category.objects.create(
        name="Knee Braces",
        slug="knee-braces",
        description="Support for knee injuries",
    )


@pytest.fixture
def product(category):
    return Product.objects.create(
        category=category,
        name="Professional Knee Brace",
        slug="professional-knee-brace",
        description="High-quality knee brace for sports injuries",
        price=49.99,
        stock=100,
        injury_type=Product.INJURY_TYPE_KNEE,
        brand="HooperZone",
        size="L",
    )


@pytest.mark.django_db
class TestOTPAuthentication:
    def test_send_otp_for_registration(self, api_client, settings):
        settings.OTP_RETURN_IN_RESPONSE = True
        url = reverse("accounts:otp-send")
        response = api_client.post(url, {"phone": "+1987654321", "otp_type": "register"})
        assert response.status_code == status.HTTP_200_OK
        assert "otp" in response.data
        assert response.data["phone"] == "+1987654321"

    def test_send_otp_for_existing_user_login(self, api_client, user, settings):
        settings.OTP_RETURN_IN_RESPONSE = True
        url = reverse("accounts:otp-send")
        response = api_client.post(url, {"phone": user.phone, "otp_type": "login"})
        assert response.status_code == status.HTTP_200_OK
        assert "otp" in response.data

    def test_send_otp_for_nonexistent_user_login(self, api_client):
        url = reverse("accounts:otp-send")
        response = api_client.post(url, {"phone": "+1111111111", "otp_type": "login"})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_verify_otp_and_login(self, api_client, user):
        otp = OTPCode.objects.create(user=user, otp_type=OTPCode.OTP_TYPE_LOGIN)
        url = reverse("accounts:otp-verify")
        response = api_client.post(
            url,
            {"phone": user.phone, "code": otp.code, "otp_type": "login"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]

    def test_verify_wrong_otp(self, api_client, user):
        url = reverse("accounts:otp-verify")
        response = api_client.post(
            url,
            {"phone": user.phone, "code": "000000", "otp_type": "login"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_user(self, api_client):
        url = reverse("accounts:register")
        response = api_client.post(
            url,
            {
                "phone": "+1555555555",
                "password": "securepass123",
                "first_name": "John",
                "last_name": "Doe",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "tokens" in response.data

    def test_register_duplicate_phone(self, api_client, user):
        url = reverse("accounts:register")
        response = api_client.post(
            url,
            {"phone": user.phone, "password": "securepass123"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_with_username(self, api_client):
        url = reverse("accounts:register")
        response = api_client.post(
            url,
            {
                "username": "newuser123",
                "password": "securepass123",
                "first_name": "New",
                "last_name": "User",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert "tokens" in response.data
        assert response.data["user"]["username"] == "newuser123"

    def test_register_duplicate_username(self, api_client):
        User.objects.create_user(username="existinguser", password="securepass123")
        url = reverse("accounts:register")
        response = api_client.post(
            url,
            {"username": "existinguser", "password": "securepass123"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_login_with_username_and_password(self, api_client):
        User.objects.create_user(username="loginuser", phone="09199999999", password="securepass123")
        url = reverse("accounts:login")
        response = api_client.post(
            url,
            {"username": "loginuser", "password": "securepass123"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]
        assert response.data["user"]["username"] == "loginuser"

    def test_login_with_phone_and_password(self, api_client, user):
        url = reverse("accounts:login")
        response = api_client.post(
            url,
            {"phone": user.phone, "password": "testpass123"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]

    def test_login_with_invalid_credentials(self, api_client, user):
        url = reverse("accounts:login")
        response = api_client.post(
            url,
            {"phone": user.phone, "password": "wrongpassword"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_profile_access_authenticated(self, authenticated_client):
        url = reverse("accounts:profile")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["phone"] == "+1234567890"

    def test_profile_access_unauthenticated(self, api_client):
        url = reverse("accounts:profile")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestProducts:
    def test_list_categories(self, api_client, category):
        url = reverse("products:category-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_list_products(self, api_client, product):
        url = reverse("products:product-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_product_detail(self, api_client, product):
        url = reverse("products:product-detail", kwargs={"slug": product.slug})
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == product.name

    def test_filter_products_by_injury_type(self, api_client, product):
        url = reverse("products:product-list")
        response = api_client.get(url, {"injury_type": "knee"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_search_products(self, api_client, product):
        url = reverse("products:product-list")
        response = api_client.get(url, {"search": "knee"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_injury_types_endpoint(self, api_client):
        url = reverse("products:product-injury-types")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert "knee" in response.data


@pytest.mark.django_db
class TestCart:
    def test_get_empty_cart(self, authenticated_client):
        url = reverse("cart:cart-detail")
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_items"] == 0

    def test_add_item_to_cart(self, authenticated_client, product):
        url = reverse("cart:cart-add")
        response = authenticated_client.post(
            url, {"product_id": product.id, "quantity": 2}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_items"] == 2

    def test_update_cart_item(self, authenticated_client, product):
        add_url = reverse("cart:cart-add")
        authenticated_client.post(add_url, {"product_id": product.id, "quantity": 1})

        cart_url = reverse("cart:cart-detail")
        cart_response = authenticated_client.get(cart_url)
        item_id = cart_response.data["items"][0]["id"]

        update_url = reverse("cart:cart-update")
        response = authenticated_client.patch(
            update_url, {"item_id": item_id, "quantity": 3}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_items"] == 3

    def test_remove_cart_item(self, authenticated_client, product):
        add_url = reverse("cart:cart-add")
        authenticated_client.post(add_url, {"product_id": product.id, "quantity": 1})

        cart_url = reverse("cart:cart-detail")
        cart_response = authenticated_client.get(cart_url)
        item_id = cart_response.data["items"][0]["id"]

        remove_url = reverse("cart:cart-remove")
        response = authenticated_client.delete(
            remove_url, {"item_id": item_id}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_items"] == 0

    def test_clear_cart(self, authenticated_client, product):
        add_url = reverse("cart:cart-add")
        authenticated_client.post(add_url, {"product_id": product.id, "quantity": 5})

        clear_url = reverse("cart:cart-clear")
        response = authenticated_client.delete(clear_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_items"] == 0


@pytest.mark.django_db
class TestOrders:
    def test_create_order(self, authenticated_client, product):
        cart_url = reverse("cart:cart-add")
        authenticated_client.post(cart_url, {"product_id": product.id, "quantity": 2})

        order_url = reverse("orders:order-create")
        response = authenticated_client.post(
            order_url,
            {
                "shipping_address": "123 Main St",
                "shipping_city": "New York",
                "shipping_state": "NY",
                "shipping_zip": "10001",
                "shipping_country": "US",
                "shipping_phone": "+1234567890",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        # Two items at 49.99 plus the default Post fee from shop settings.
        assert response.data["shipping_method"] == "post"
        assert response.data["total"] == "60099.98"

    def test_list_orders(self, authenticated_client, product):
        cart_url = reverse("cart:cart-add")
        authenticated_client.post(cart_url, {"product_id": product.id, "quantity": 1})

        order_url = reverse("orders:order-create")
        authenticated_client.post(
            order_url,
            {
                "shipping_address": "123 Main St",
                "shipping_city": "New York",
                "shipping_state": "NY",
                "shipping_zip": "10001",
                "shipping_country": "US",
                "shipping_phone": "+1234567890",
            },
        )

        list_url = reverse("orders:order-list")
        response = authenticated_client.get(list_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_cancel_order(self, authenticated_client, product):
        cart_url = reverse("cart:cart-add")
        authenticated_client.post(cart_url, {"product_id": product.id, "quantity": 1})

        order_url = reverse("orders:order-create")
        order_response = authenticated_client.post(
            order_url,
            {
                "shipping_address": "123 Main St",
                "shipping_city": "New York",
                "shipping_state": "NY",
                "shipping_zip": "10001",
                "shipping_country": "US",
                "shipping_phone": "+1234567890",
            },
        )

        order_number = order_response.data["order_number"]
        cancel_url = reverse("orders:order-cancel", kwargs={"order_number": order_number})
        response = authenticated_client.post(cancel_url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "cancelled"


@pytest.mark.django_db
class TestReviews:
    def test_create_review(self, authenticated_client, product):
        url = reverse("reviews:review-create", kwargs={"product_slug": product.slug})
        response = authenticated_client.post(
            url,
            {"rating": 5, "title": "Excellent product", "comment": "Very helpful for my knee recovery"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["rating"] == 5

    def test_list_product_reviews(self, api_client, authenticated_client, product):
        create_url = reverse("reviews:review-create", kwargs={"product_slug": product.slug})
        authenticated_client.post(
            create_url,
            {"rating": 4, "title": "Good", "comment": "Works well"},
        )

        list_url = reverse("reviews:product-reviews", kwargs={"product_slug": product.slug})
        response = api_client.get(list_url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_duplicate_review_rejected(self, authenticated_client, product):
        url = reverse("reviews:review-create", kwargs={"product_slug": product.slug})
        authenticated_client.post(
            url,
            {"rating": 5, "title": "Great", "comment": "Love it"},
        )
        response = authenticated_client.post(
            url,
            {"rating": 3, "title": "Changed mind", "comment": "Actually not great"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserProfileAddress:
    def test_update_profile_address_and_city(self, authenticated_client):
        url = reverse("accounts:profile")
        payload = {
            "first_name": "Ali",
            "last_name": "Rezaei",
            "address": "خیابان آزادی پلاک ۱۰",
            "province": "تهران",
            "city": "تهران",
            "postal_code": "1234567890",
        }
        response = authenticated_client.put(url, payload)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["province"] == "تهران"
        assert response.data["city"] == "تهران"
        assert response.data["postal_code"] == "1234567890"


@pytest.mark.django_db
class TestLocalizationEndpoints:
    def test_product_localization_parameter(self, api_client, category):
        product = Product.objects.create(
            category=category,
            name="English Knee Brace",
            name_fa="بریس زانوی فارسی",
            slug="localized-knee-brace",
            description="English description",
            description_fa="توضیحات فارسی",
            price=50.00,
            stock=10,
        )
        url = reverse("products:product-detail", kwargs={"slug": product.slug})

        # Default / English
        res_en = api_client.get(f"{url}?lang=en")
        assert res_en.status_code == status.HTTP_200_OK
        assert res_en.data["name_localized"] == "English Knee Brace"

        # Persian
        res_fa = api_client.get(f"{url}?lang=fa")
        assert res_fa.status_code == status.HTTP_200_OK
        assert res_fa.data["name_localized"] == "بریس زانوی فارسی"
        assert res_fa.data["description_localized"] == "توضیحات فارسی"


@pytest.mark.django_db
class TestOrderPayments:
    def test_payment_initiation_and_verification(self, authenticated_client, user, product):
        from cart.models import Cart, CartItem
        from orders.models import Order

        cart = Cart.objects.create(user=user)
        CartItem.objects.create(cart=cart, product=product, quantity=2)

        # Create order
        create_url = reverse("orders:order-create")
        order_res = authenticated_client.post(
            create_url,
            {
                "shipping_address": "Tehran, Azadi St",
                "shipping_city": "Tehran",
                "shipping_state": "Tehran",
                "shipping_zip": "1234567890",
                "shipping_country": "IR",
                "shipping_phone": "09121234567",
            },
        )
        assert order_res.status_code == status.HTTP_201_CREATED
        order_number = order_res.data["order_number"]

        # Initiate payment
        pay_url = reverse("orders:order-pay-initiate", kwargs={"order_number": order_number})
        initiate_res = authenticated_client.post(pay_url, {"gateway": "zarinpal"})
        assert initiate_res.status_code == status.HTTP_200_OK
        assert "authority" in initiate_res.data
        authority = initiate_res.data["authority"]

        # Verify payment
        verify_url = reverse("orders:order-pay-verify")
        verify_res = authenticated_client.post(
            verify_url,
            {
                "order_number": order_number,
                "authority": authority,
                "gateway": "zarinpal",
            },
        )
        assert verify_res.status_code == status.HTTP_200_OK
        assert verify_res.data["success"] is True

        order = Order.objects.get(order_number=order_number)
        assert order.payment_status == Order.PAYMENT_STATUS_PAID
        assert order.status == Order.STATUS_CONFIRMED

