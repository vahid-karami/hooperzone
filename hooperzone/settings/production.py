"""
Production settings (used on Wispbyte, see DEPLOY_WISPBYTE.md).

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

ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "hooperzone.ir,www.hooperzone.ir").split(",") if h]
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o]

# Cloudflare terminates TLS in front of the app and forwards plain HTTP.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# Set SECURE_COOKIES=False only while testing over plain http://<ip>:<port> (Django admin login).
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = os.environ.get("SECURE_COOKIES", "True") == "True"

# SQLite in <project>/database (kept between deploys: the deploy zip never contains it).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": PROJECT_ROOT / "database" / "db.sqlite3",
    }
}

# No nginx on Wispbyte: WhiteNoise serves /static and Django serves /media (see hooperzone/urls.py).
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STATIC_URL = "/static/"
STATIC_ROOT = PROJECT_ROOT / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = PROJECT_ROOT / "media"
SERVE_MEDIA = True
