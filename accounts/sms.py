"""Send OTP codes by SMS through SMS.ir (https://app.sms.ir/developer/help/verify)."""
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

SMSIR_VERIFY_URL = "https://api.sms.ir/v1/send/verify"


class SMSError(Exception):
    pass


def sms_configured():
    return bool(getattr(settings, "SMSIR_API_KEY", "") and getattr(settings, "SMSIR_TEMPLATE_ID", ""))


def send_otp_sms(phone, code):
    """Send `code` to `phone` with the SMS.ir verify template. Raises SMSError on failure.

    Without SMS.ir settings (development) the code is only written to the log.
    """
    if not sms_configured():
        logger.warning("SMS.ir is not configured; OTP for %s is %s", phone, code)
        return False

    payload = {
        "mobile": phone,
        "templateId": int(settings.SMSIR_TEMPLATE_ID),
        "parameters": [{"name": getattr(settings, "SMSIR_CODE_PARAMETER", "CODE"), "value": str(code)}],
    }
    req = urllib.request.Request(
        SMSIR_VERIFY_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "text/plain",
            "x-api-key": settings.SMSIR_API_KEY,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        logger.error("SMS.ir rejected OTP to %s: %s %s", phone, e.code, body)
        raise SMSError(body) from e
    except Exception as e:
        logger.error("SMS.ir request failed for %s: %s", phone, e)
        raise SMSError(str(e)) from e

    if result.get("status") != 1:
        logger.error("SMS.ir did not send OTP to %s: %s", phone, result)
        raise SMSError(result.get("message") or "SMS not sent")
    return True
