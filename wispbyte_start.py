"""Start HooperZone on Wispbyte (Pterodactyl Python egg). See DEPLOY_WISPBYTE.md.

Set the egg's "App py file" to wispbyte_start.py. On every boot this:
1. creates .env with a random SECRET_KEY the first time (the panel has no free-form env vars),
2. runs migrations, collects static files, loads the demo catalogue once and creates the
   admin user from ADMIN_PHONE / ADMIN_PASSWORD in .env,
3. serves the site with Waitress on the port Wispbyte assigned (SERVER_PORT).

Auto-deploy (on the Wispbyte server only): GitHub Actions publishes every tested push to master
as a ready-to-run bundle on the `deploy` branch (.github/workflows/ci-cd.yml). This script installs
the newest bundle on boot and checks for a new one every AUTO_DEPLOY_INTERVAL seconds, then
restarts itself. .env, database/, media/ and logs/ are never touched.

Works locally too: `python wispbyte_start.py` then open http://localhost:8000.
"""
import io
import os
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
VERSION_FILE = ROOT / ".deployed_version"
# Server-only data that a release never overwrites (pip packages live in .local).
KEEP = {".env", ".deployed_version", "database", "media", "logs", "staticfiles", ".local", ".cache"}

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


def auto_deploy_settings():
    """(repo, branch, check interval in seconds) when auto-deploy is on, else None.

    AUTO_DEPLOY=auto (default) turns it on only on a Pterodactyl server (P_SERVER_UUID is set),
    so running this script on your PC never replaces your code. A git checkout is never touched.
    """
    mode = os.environ.get("AUTO_DEPLOY", "auto").lower()
    enabled = mode == "true" or (mode == "auto" and "P_SERVER_UUID" in os.environ)
    if not enabled or (ROOT / ".git").exists():
        return None
    repo = os.environ.get("AUTO_DEPLOY_REPO", "vahid-karami/hooperzone")
    branch = os.environ.get("AUTO_DEPLOY_BRANCH", "deploy")
    return repo, branch, int(os.environ.get("AUTO_DEPLOY_INTERVAL", "300"))


def fetch(url, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": "hooperzone-autodeploy"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def remote_version(repo, branch):
    # The query string skips GitHub's raw-file cache, so a new release is seen right away.
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/DEPLOY_VERSION?t={int(time.time())}"
    return fetch(url).decode().strip()


def local_version():
    return VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else ""


def install_release(zip_bytes, root=ROOT):
    """Unpack a GitHub branch zip over `root`, keeping server data (KEEP). Returns its version."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        prefix = names[0].split("/")[0] + "/"  # GitHub wraps the branch in "<repo>-<branch>/"
        files = {n[len(prefix):]: n for n in names if n.startswith(prefix) and not n.endswith("/")}
        for required in ("wispbyte_start.py", "manage.py", "frontend/dist/index.html", "DEPLOY_VERSION"):
            if required not in files:
                raise ValueError(f"Not a HooperZone release: {required} is missing.")
        shutil.rmtree(root / "frontend" / "dist", ignore_errors=True)  # drop old hashed assets
        for rel, name in files.items():
            if rel.split("/")[0] in KEEP:
                continue
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(name) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)
        return zf.read(files["DEPLOY_VERSION"]).decode().strip()


def deploy_release(repo, branch):
    """Download and install the newest release, plus any new Python packages."""
    requirements = ROOT / "requirements.txt"
    old_requirements = requirements.read_bytes() if requirements.exists() else b""
    data = fetch(f"https://codeload.github.com/{repo}/zip/refs/heads/{branch}", timeout=120)
    version = install_release(data)
    if requirements.read_bytes() != old_requirements:
        print("requirements.txt changed: installing packages...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-U", "--prefix", ".local", "-r", "requirements.txt"])
    VERSION_FILE.write_text(version, encoding="utf-8")
    print(f"Deployed version {version[:7]}.")


def restart():
    print("Restarting with the new version...")
    sys.stdout.flush()
    os.execv(sys.executable, [sys.executable, str(ROOT / "wispbyte_start.py")])


def sync_on_boot():
    """Install a newer release before starting; restart into it so the new start script runs."""
    settings = auto_deploy_settings()
    if not settings:
        return
    repo, branch, _ = settings
    try:
        remote = remote_version(repo, branch)
        if remote == local_version():
            print(f"Auto-deploy: up to date ({remote[:7]}).")
            return
        print(f"Auto-deploy: installing {remote[:7]} from {repo}@{branch}...")
        deploy_release(repo, branch)
    except Exception as e:  # never block the site from starting
        print(f"Auto-deploy skipped: {e}")
        return
    restart()


def watch_for_releases():
    settings = auto_deploy_settings()
    if not settings or settings[2] <= 0:
        return
    repo, branch, interval = settings

    def loop():
        while True:
            time.sleep(interval)
            try:
                remote = remote_version(repo, branch)
                if remote and remote != local_version():
                    print(f"Auto-deploy: new version {remote[:7]} found.")
                    deploy_release(repo, branch)
                    restart()
            except Exception as e:
                print(f"Auto-deploy check failed: {e}")

    threading.Thread(target=loop, name="auto-deploy", daemon=True).start()
    print(f"Auto-deploy: checking {repo}@{branch} every {interval}s.")


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
    call_command("setup_roles")  # the "Product editors" staff group
    call_command("seed_size_guides")  # starter size guides to pick from (created once, never overwritten)
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
    sync_on_boot()
    prepare()
    watch_for_releases()
    serve()
