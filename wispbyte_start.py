"""Boot HooperZone in production. ParsPack PaaS runs it through app.py; see DEPLOY_PARSPACK.md.

On every boot this:
1. creates DATA_DIR/.env with a random SECRET_KEY the first time,
2. runs migrations, collects static files, loads the demo catalogue once and creates the
   admin user from ADMIN_PHONE / ADMIN_PASSWORD in .env,
3. serves the site with Waitress on SERVER_PORT (8000 on ParsPack).

New versions are built by ParsPack from the `deploy` branch (GitHub webhook), so this script
never updates itself.

Works locally too: `python app.py` then open http://localhost:8000.
"""
import os
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
# Server data (.env, database/, media/, logs/). ParsPack PaaS sets DATA_DIR to its permanent disk.
DATA_DIR = Path(os.environ.get("DATA_DIR") or ROOT)
ENV_FILE = DATA_DIR / ".env"

DEFAULT_ENV = """\
# Created on first boot. Settings in the ParsPack panel (environment variables) win over this file.
SECRET_KEY={secret_key}
DEBUG=False
ALLOWED_HOSTS=hooperzone.ir,www.hooperzone.ir,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://hooperzone.ir,https://www.hooperzone.ir
# False only while testing the Django admin over plain http.
SECURE_COOKIES=True
SITE_URL=https://hooperzone.ir
# ZarinPal: paste the merchant ID from your ZarinPal panel. While PAYMENT_SANDBOX=True,
# payments go to sandbox.zarinpal.com and no real money is taken.
PAYMENT_SANDBOX=False
ZARINPAL_MERCHANT_ID=
# SMS.ir: API key from app.sms.ir > Developers, and the ID of a verify template with a CODE parameter.
SMSIR_API_KEY=
SMSIR_TEMPLATE_ID=
# Once https://hooperzone.ir works everywhere, set e.g. 31536000 (browsers then insist on https).
SECURE_HSTS_SECONDS=0
# Fill both and restart once to create the Django admin user, then delete ADMIN_PASSWORD.
ADMIN_PHONE=
ADMIN_PASSWORD=
"""


def ensure_env_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not ENV_FILE.exists():
        ENV_FILE.write_text(DEFAULT_ENV.format(secret_key=secrets.token_urlsafe(50)), encoding="utf-8")
        print(f"Created {ENV_FILE.name} with a new SECRET_KEY.")
    load_dotenv(ENV_FILE)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hooperzone.settings.production")


def prepare():
    import django
    from django.core.management import call_command

    django.setup()
    (DATA_DIR / "database").mkdir(exist_ok=True)
    (DATA_DIR / "media").mkdir(exist_ok=True)
    call_command("migrate", interactive=False)
    call_command("collectstatic", interactive=False, verbosity=0)
    call_command("seed_demo_store")  # first boot only: skips when products exist
    call_command("seed_category_images")  # fills missing category photos only
    call_command("seed_sports")  # never replaces photos uploaded in the admin
    call_command("build_thumbnails")  # small WebP copies for images that don't have one yet
    call_command("watermark_product_images")  # shop logo on product photos that don't have it yet
    call_command("cancel_unpaid_orders")  # release stock held by abandoned checkouts
    call_command("backup_db")  # daily copy of the SQLite database, keeps the last 7
    call_command("setup_roles")  # the "Product editors" staff group
    call_command("seed_size_guides")  # starter size guides to pick from (created once, never overwritten)
    create_admin()


def create_admin():
    """There is no shell for createsuperuser on the host, so ADMIN_* in .env create the first admin."""
    from django.contrib.auth import get_user_model

    phone, password = os.environ.get("ADMIN_PHONE"), os.environ.get("ADMIN_PASSWORD")
    if not (phone and password):
        return
    User = get_user_model()
    if User.objects.filter(phone=phone).exists():
        print(f"Admin {phone} already exists; you can remove ADMIN_PASSWORD from .env.")
        return
    User.objects.create_superuser(phone=phone, password=password)
    print(f"Created admin user {phone}. Remove ADMIN_PASSWORD from .env now.")


def serve():
    from waitress import serve as waitress_serve

    from hooperzone.wsgi import application

    port = int(os.environ.get("SERVER_PORT") or os.environ.get("PORT") or 8000)
    print(f"HooperZone is running on port {port}")
    waitress_serve(
        application,
        host="0.0.0.0",
        port=port,
        threads=int(os.environ.get("WAITRESS_THREADS", 6)),
        # The ParsPack ingress terminates TLS; trust its scheme header so Django knows it was HTTPS.
        trusted_proxy="*",
        trusted_proxy_headers={"x-forwarded-proto"},
        clear_untrusted_proxy_headers=True,
    )


def main():
    sys.stdout.reconfigure(line_buffering=True)  # logs are a pipe; show progress live
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    ensure_env_file()
    prepare()
    serve()


if __name__ == "__main__":
    main()
