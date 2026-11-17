"""
Production settings (ParsPack PaaS, see DEPLOY_PARSPACK.md).

Select with DJANGO_SETTINGS_MODULE=hooperzone.settings.production. Everything
environment-specific comes from environment variables or the project's .env file.
"""
import os

from .base import *  # noqa

DEBUG = os.environ.get("DEBUG", "False") == "True"

if SECRET_KEY.startswith("django-insecure"):  # noqa: F405
    raise RuntimeError("SECRET_KEY must be set in the environment for production.")

# BASE_DIR is the inner "hooperzone" package; the deployed project root is one level up.
PROJECT_ROOT = BASE_DIR.parent  # noqa: F405
# Where the database, uploads and logs live. On ParsPack PaaS this is the permanent disk
# (DATA_DIR=/data); without DATA_DIR it is the project folder.
DATA_DIR = Path(os.environ.get("DATA_DIR") or PROJECT_ROOT)  # noqa: F405

ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "hooperzone.ir,www.hooperzone.ir").split(",") if h]
CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "https://hooperzone.ir,https://www.hooperzone.ir").split(",") if o
]

# ParsPack's ingress terminates TLS in front of the app and forwards plain HTTP.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Set SECURE_COOKIES=False only while testing over plain http://<ip>:<port> (Django admin login).
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = os.environ.get("SECURE_COOKIES", "True") == "True"

# SQLite in DATA_DIR/database (kept between deploys: the release bundle never contains it).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_DIR / "database" / "db.sqlite3",
    }
}

# No separate web server: WhiteNoise serves /static and Django serves /media (see hooperzone/urls.py).
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STATIC_URL = "/static/"
STATIC_ROOT = PROJECT_ROOT / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = DATA_DIR / "media"
SERVE_MEDIA = True

# collectstatic writes .gz copies, so WhiteNoise sends the 340 KB main bundle as ~105 KB.
# No manifest storage: Vite already puts a content hash in every file name under assets/.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}


def _vite_hashed(path, url):
    """Vite bundles (assets/name-<hash>.ext) never change, so browsers may keep them a year."""
    return url.startswith(STATIC_URL + "assets/")


WHITENOISE_IMMUTABLE_FILE_TEST = _vite_hashed

# Security headers. Turn on HSTS (e.g. SECURE_HSTS_SECONDS=31536000) only once
# https://hooperzone.ir and www both have working certificates (ParsPack free SSL): browsers
# then refuse plain http for that long.
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# OTP codes in API responses let anyone sign in as anyone. Never on the live site,
# whatever an old .env says.
OTP_RETURN_IN_RESPONSE = False
PAYMENT_MOCK_FALLBACK = False
# Codes can only reach customers by SMS here, so a missing SMS.ir config is an error.
SMS_REQUIRED = True

LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "django.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "formatter": "plain",
            "encoding": "utf-8",
        },
    },
    "root": {"handlers": ["console", "file"], "level": "WARNING"},
    "loggers": {
        "orders": {"level": "INFO"},
        "accounts": {"level": "INFO"},
    },
}

import logging as _logging  # noqa: E402

if not PAYMENT_SANDBOX and not ZARINPAL_MERCHANT_ID:  # noqa: F405
    _logging.getLogger("orders").warning(
        "PAYMENT_SANDBOX is off but ZARINPAL_MERCHANT_ID is empty: customers cannot pay."
    )
if PAYMENT_SANDBOX:  # noqa: F405
    _logging.getLogger("orders").warning(
        "PAYMENT_SANDBOX is on: payments go to sandbox.zarinpal.com and no real money is taken."
    )
