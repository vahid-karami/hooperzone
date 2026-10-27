from pathlib import Path
from datetime import timedelta

from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-change-me-in-production")

DEBUG = os.environ.get("DEBUG", "True") == "True"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    # external packages
    "rest_framework",
    "corsheaders",
    # internal apps
    "accounts",
    "products",
    "cart",
    "orders",
    "reviews",
    "favorites",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "hooperzone.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "hooperzone.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Tehran"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Built React app (npm run build:django). Its assets are collected as static files
# and its index.html is served for all non-API URLs (see hooperzone/urls.py).
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
STATICFILES_DIRS = [FRONTEND_DIST] if FRONTEND_DIST.exists() else []
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

CORS_ALLOW_CREDENTIALS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_RATES": {
        "otp": os.environ.get("OTP_THROTTLE_RATE", "10/min"),
        "auth": os.environ.get("AUTH_THROTTLE_RATE", "10/min"),
    },
}

# Sandbox mode talks to sandbox.zarinpal.com. When the sandbox is unreachable in
# development, an offline mock gateway (auto-approved fake payments) stands in.
# production.py turns the mock off: it would let anyone mark an order paid.
PAYMENT_SANDBOX = os.environ.get("PAYMENT_SANDBOX", str(DEBUG)) == "True"
PAYMENT_MOCK_FALLBACK = DEBUG
ZARINPAL_MERCHANT_ID = os.environ.get("ZARINPAL_MERCHANT_ID", "").strip()
IDPAY_API_KEY = os.environ.get("IDPAY_API_KEY", "").strip()

# SMS.ir verify template for OTP codes. The template needs one parameter named CODE.
SMSIR_API_KEY = os.environ.get("SMSIR_API_KEY", "").strip()
SMSIR_TEMPLATE_ID = os.environ.get("SMSIR_TEMPLATE_ID", "").strip()
SMSIR_CODE_PARAMETER = os.environ.get("SMSIR_CODE_PARAMETER", "CODE").strip()

# Only expose OTP codes in API responses while developing. Production forces this off.
OTP_RETURN_IN_RESPONSE = os.environ.get("OTP_RETURN_IN_RESPONSE", str(DEBUG)) == "True"

SITE_URL = os.environ.get("SITE_URL", "https://hooperzone.ir").rstrip("/")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

AUTHENTICATION_BACKENDS = [
    "accounts.backends.PhoneOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]
