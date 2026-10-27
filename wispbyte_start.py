"""Start HooperZone on Wispbyte (Pterodactyl Python egg). See DEPLOY_WISPBYTE.md.

Set the egg's "App py file" to wispbyte_start.py. On every boot this:
1. creates .env with a random SECRET_KEY the first time (the panel has no free-form env vars),
2. runs migrations, collects static files, loads the demo catalogue once and creates the
   admin user from ADMIN_PHONE / ADMIN_PASSWORD in .env,
3. serves the site with Waitress on the port Wispbyte assigned (SERVER_PORT).

Works locally too: `python wispbyte_start.py` then open http://localhost:8000.
"""
import os
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"

DEFAULT_ENV = """\
# Created by wispbyte_start.py on first boot. Edit in the Wispbyte file manager, then restart.
SECRET_KEY={secret_key}
DEBUG=False
ALLOWED_HOSTS=hooperzone.ir,www.hooperzone.ir,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://hooperzone.ir,https://www.hooperzone.ir
# False only while testing the Django admin over plain http://<ip>:<port>.
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
    if not ENV_FILE.exists():
        ENV_FILE.write_text(DEFAULT_ENV.format(secret_key=secrets.token_urlsafe(50)), encoding="utf-8")
        print(f"Created {ENV_FILE.name} with a new SECRET_KEY.")
    load_dotenv(ENV_FILE)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hooperzone.settings.production")
    # Pterodactyl exposes the server's public IP; allow it so http://<ip>:<port> works for testing.
    server_ip = os.environ.get("SERVER_IP", "")
    if server_ip and server_ip != "0.0.0.0":
        os.environ["ALLOWED_HOSTS"] = f"{os.environ.get('ALLOWED_HOSTS', '')},{server_ip}"


def prepare():
    import django
    from django.core.management import call_command

    django.setup()
    (ROOT / "database").mkdir(exist_ok=True)
    (ROOT / "media").mkdir(exist_ok=True)
    call_command("migrate", interactive=False)
    call_command("collectstatic", interactive=False, verbosity=0)
    call_command("seed_demo_store")  # first boot only: skips when products exist
    call_command("seed_category_images")  # fills missing category photos only
    call_command("seed_sports")  # never replaces photos uploaded in the admin
    call_command("build_thumbnails")  # small WebP copies for images that don't have one yet
    call_command("cancel_unpaid_orders")  # release stock held by abandoned checkouts
    call_command("backup_db")  # daily copy of the SQLite database, keeps the last 7
    create_admin()


def create_admin():
    """The panel console is not a shell, so createsuperuser can't run there. Use ADMIN_* in .env instead."""
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
        # Cloudflare sits in front; trust its scheme header so Django knows the request was HTTPS.
        trusted_proxy="*",
        trusted_proxy_headers={"x-forwarded-proto"},
        clear_untrusted_proxy_headers=True,
    )


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)  # the panel console is a pipe; show progress live
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    ensure_env_file()
    prepare()
    serve()
