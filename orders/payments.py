import json
import logging
import uuid
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


class PaymentGatewayError(Exception):
    pass


def mock_return_url(callback_url, **params):
    """Sandbox only: skip the gateway page and go straight back to the callback, like a paid transaction would."""
    separator = "&" if urllib.parse.urlparse(callback_url).query else "?"
    return f"{callback_url}{separator}{urllib.parse.urlencode(params)}"


def mock_payments_allowed(sandbox):
    """Offline mock transactions auto-succeed, so they must never exist on the live site."""
    return sandbox and getattr(settings, "PAYMENT_MOCK_FALLBACK", False)


def toman_amount(order):
    """Order total in Tomans (prices are stored in Tomans)."""
    return int(order.total)


def rial_amount(order):
    """Order total in Rials."""
    return int(order.total) * 10


def _post_json(url, payload, headers=None, timeout=10):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # ZarinPal v4 answers errors with 4xx and a JSON body.
        try:
            return json.loads(e.read().decode("utf-8"))
        except Exception:
            raise e


class ZarinPalGateway:
    """
    ZarinPal REST API v4 (https://www.zarinpal.com/docs/paymentGateway/).
    Amounts are sent in Tomans (currency "IRT").
    """

    SANDBOX_MERCHANT = "00000000-0000-0000-0000-000000000000"

    def __init__(self, merchant_id=None, sandbox=True):
        self.sandbox = sandbox
        self.merchant_id = merchant_id or getattr(settings, "ZARINPAL_MERCHANT_ID", "") or (
            self.SANDBOX_MERCHANT if sandbox else ""
        )

    @property
    def host(self):
        return "https://sandbox.zarinpal.com" if self.sandbox else "https://payment.zarinpal.com"

    def get_request_url(self):
        return f"{self.host}/pg/v4/payment/request.json"

    def get_startpay_url(self, authority):
        return f"{self.host}/pg/StartPay/{authority}"

    def get_verify_url(self):
        return f"{self.host}/pg/v4/payment/verify.json"

    def request_payment(self, order, callback_url, description=None):
        """Start a transaction and return the gateway redirect URL and authority code."""
        amount = toman_amount(order)
        payload = {
            "merchant_id": self.merchant_id,
            "amount": amount,
            "currency": "IRT",
            "description": description or f"سفارش {order.order_number} - هوپرزون",
            "callback_url": callback_url,
            "metadata": {
                "mobile": getattr(order.user, "phone", "") or order.shipping_phone,
                "email": getattr(order.user, "email", "") or "",
                "order_id": order.order_number,
            },
        }

        try:
            if not self.merchant_id:
                raise PaymentGatewayError("ZARINPAL_MERCHANT_ID is not configured.")
            result = _post_json(self.get_request_url(), payload)
            data = result.get("data") or {}
            if isinstance(data, dict) and data.get("code") == 100 and data.get("authority"):
                authority = data["authority"]
                return {
                    "success": True,
                    "authority": authority,
                    "payment_url": self.get_startpay_url(authority),
                    "amount": amount,
                }
            raise PaymentGatewayError(f"ZarinPal request failed: {result.get('errors') or data}")
        except Exception as e:
            if not mock_payments_allowed(self.sandbox):
                logger.error("ZarinPal request failed for %s: %s", order.order_number, e)
                if isinstance(e, PaymentGatewayError):
                    raise
                raise PaymentGatewayError(str(e)) from e
            logger.warning("ZarinPal sandbox unreachable (%s). Using a local mock authority.", e)
            authority = f"ZP-MOCK-{uuid.uuid4().hex[:12]}"
            return {
                "success": True,
                "authority": authority,
                "payment_url": mock_return_url(callback_url, Authority=authority, Status="OK"),
                "amount": amount,
                "is_mock": True,
            }

    def verify_payment(self, order, authority):
        if authority.startswith("ZP-MOCK-"):
            if mock_payments_allowed(self.sandbox):
                return {
                    "success": True,
                    "ref_id": f"REF-{uuid.uuid4().hex[:8].upper()}",
                    "status": 100,
                    "is_mock": True,
                }
            return {"success": False, "error": "Invalid payment authority."}

        payload = {
            "merchant_id": self.merchant_id,
            "authority": authority,
            # Must match the amount sent in request_payment or ZarinPal rejects it.
            "amount": toman_amount(order),
        }

        try:
            result = _post_json(self.get_verify_url(), payload)
            data = result.get("data") or {}
            code = data.get("code") if isinstance(data, dict) else None
            if code in (100, 101):
                return {
                    "success": True,
                    "ref_id": str(data.get("ref_id", "")),
                    "card_pan": data.get("card_pan", "") or "",
                    "status": code,
                }
            return {
                "success": False,
                "error": f"Payment verification failed: {result.get('errors') or code}",
            }
        except Exception as e:
            logger.error("ZarinPal verification error for %s: %s", order.order_number, e)
            return {"success": False, "error": str(e)}


class IDPayGateway:
    """
    IDPay payment gateway service.
    """
    def __init__(self, api_key=None, sandbox=True):
        self.api_key = api_key or getattr(settings, "IDPAY_API_KEY", "") or ("mock-idpay-api-key" if sandbox else "")
        self.sandbox = sandbox

    def get_headers(self):
        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key,
        }
        if self.sandbox:
            headers["X-SANDBOX"] = "1"
        return headers

    def request_payment(self, order, callback_url, description=None):
        amount_irr = rial_amount(order)
        desc = description or f"Payment for Order {order.order_number}"

        payload = {
            "order_id": order.order_number,
            "amount": amount_irr,
            "name": order.user.get_full_name() if hasattr(order.user, "get_full_name") else "",
            "phone": getattr(order.user, "phone", order.shipping_phone),
            "mail": getattr(order.user, "email", ""),
            "desc": desc,
            "callback": callback_url,
        }

        try:
            req = urllib.request.Request(
                "https://api.idpay.ir/v1.1/payment",
                data=json.dumps(payload).encode("utf-8"),
                headers=self.get_headers(),
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode("utf-8"))
                if "link" in result:
                    return {
                        "success": True,
                        "id": result.get("id"),
                        "payment_url": result.get("link"),
                        "amount": amount_irr,
                    }
                raise PaymentGatewayError(result.get("error_message", "IDPay request failed"))
        except Exception as e:
            if not mock_payments_allowed(self.sandbox):
                logger.error(f"IDPay request failed: {e}")
                raise PaymentGatewayError(str(e)) from e
            logger.warning(f"IDPay online request failed: {e}. Generating local sandbox transaction.")
            track_id = f"IDP-MOCK-{uuid.uuid4().hex[:12]}"
            return {
                "success": True,
                "id": track_id,
                "payment_url": mock_return_url(callback_url, id=track_id, status="10"),
                "amount": amount_irr,
                "is_mock": True,
            }

    def verify_payment(self, order, payment_id):
        if str(payment_id).startswith("IDP-MOCK-"):
            if not mock_payments_allowed(self.sandbox):
                return {"success": False, "error": "Invalid payment id."}
            return {
                "success": True,
                "track_id": f"TRACK-{uuid.uuid4().hex[:8].upper()}",
                "status": 100,
                "is_mock": True,
            }

        payload = {
            "id": payment_id,
            "order_id": order.order_number,
        }

        try:
            req = urllib.request.Request(
                "https://api.idpay.ir/v1.1/payment/verify",
                data=json.dumps(payload).encode("utf-8"),
                headers=self.get_headers(),
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode("utf-8"))
                if result.get("status") == 100:
                    return {
                        "success": True,
                        "track_id": str(result.get("track_id", "")),
                        "status": result.get("status"),
                    }
                return {
                    "success": False,
                    "error": f"Verification failed with status {result.get('status')}",
                }
        except Exception as e:
            logger.error(f"IDPay verification error: {e}")
            return {"success": False, "error": str(e)}


def get_payment_gateway(gateway_name="zarinpal", sandbox=None):
    if sandbox is None:
        sandbox = getattr(settings, "PAYMENT_SANDBOX", True)
    gateways = {
        "zarinpal": ZarinPalGateway(sandbox=sandbox),
        "idpay": IDPayGateway(sandbox=sandbox),
    }
    return gateways.get(gateway_name.lower(), ZarinPalGateway(sandbox=sandbox))
