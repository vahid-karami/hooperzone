"""Start the whole project (Django + Vite) from any clone.

    python scripts/dev.py            # backend + frontend
    python scripts/dev.py backend    # backend only
    python scripts/dev.py frontend   # frontend only (expects the backend running)
    python scripts/dev.py setup      # venv, packages, migrations, demo data; then exit

First run sets everything up: virtualenv, Python and npm dependencies, migrations and
demo data. It picks a free backend port (8000 upward) and tells Vite where it is through
VITE_BACKEND_URL, so nothing machine-specific is stored in the repo.
"""
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
VENV = ROOT / "venv"
IS_WIN = os.name == "nt"
VENV_PY = VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")
NPM = shutil.which("npm.cmd" if IS_WIN else "npm") or "npm"


def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd))
    env = {**os.environ, "PYTHONUTF8": "1"}  # seed commands print Persian text
    subprocess.run([str(c) for c in cmd], check=True, cwd=kw.pop("cwd", ROOT), env=env, **kw)


def free_port(start):
    for port in range(start, start + 20):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SystemExit(f"No free port found from {start}")


def setup_backend():
    if not VENV_PY.exists():
        print("Creating virtualenv...")
        run([sys.executable, "-m", "venv", VENV])
        run([VENV_PY, "-m", "pip", "install", "-r", "requirements.txt"])
    run([VENV_PY, "manage.py", "migrate", "--noinput"])
    def count(expr):
        code = f"from products.models import Product, ProductImage; print({expr})"
        result = subprocess.run([str(VENV_PY), "manage.py", "shell", "-c", code],
                                cwd=ROOT, capture_output=True, text=True)
        if result.returncode != 0:  # never guess "0" here: the seeds below replace images
            raise SystemExit(result.stderr)
        out = result.stdout
        # Django's shell may print an "objects imported automatically" banner first.
        last = out.strip().splitlines()[-1] if out.strip() else "0"
        return int(last) if last.isdigit() else 0

    # Uploaded images and db.sqlite3 are git-ignored, so a fresh clone starts without them.
    if count("Product.objects.count()") == 0:
        print("Empty database: loading demo store...")
        run([VENV_PY, "manage.py", "seed_demo_store"])
    elif count("ProductImage.objects.count()") == 0:
        print("Products have no photos: attaching demo photos...")
        run([VENV_PY, "manage.py", "seed_product_images"])
    run([VENV_PY, "manage.py", "seed_category_images"])  # only fills categories with no image
    run([VENV_PY, "manage.py", "seed_sports"])  # sports + their photos; never replaces admin uploads
    run([VENV_PY, "manage.py", "setup_roles"])  # the "Product editors" staff group


def setup_frontend():
    if not (FRONTEND / "node_modules").exists():
        print("Installing npm packages...")
        run([NPM, "install"], cwd=FRONTEND)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    procs = []
    backend_port = int(os.environ.get("BACKEND_PORT", 0)) or free_port(8000)
    try:
        if which == "setup":
            setup_backend()
            setup_frontend()
            return
        if which in ("all", "backend"):
            setup_backend()
            print(f"Backend  -> http://localhost:{backend_port}")
            procs.append(subprocess.Popen(
                [str(VENV_PY), "manage.py", "runserver", str(backend_port)], cwd=ROOT))
        if which in ("all", "frontend"):
            setup_frontend()
            env = dict(os.environ)
            env.setdefault("VITE_BACKEND_URL", f"http://localhost:{backend_port}")
            print("Frontend -> http://localhost:5173")
            procs.append(subprocess.Popen([NPM, "run", "dev"], cwd=FRONTEND, env=env))
        while all(p.poll() is None for p in procs):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()


if __name__ == "__main__":
    main()
