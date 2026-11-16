"""Build the React app and copy everything the server needs into one folder (the release bundle).

    python scripts/build_release.py --dir OUT              # build frontend, then copy the bundle into OUT
    python scripts/build_release.py --no-build --dir OUT   # reuse the existing frontend/dist

CI publishes OUT as the `deploy` branch, which ParsPack PaaS builds and runs (DEPLOY_PARSPACK.md).
The bundle never contains .env, database/ or media/, so new versions keep live data.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
NPM = shutil.which("npm.cmd") or shutil.which("npm") or "npm"

INCLUDE = [
    "manage.py",
    "requirements.txt",
    "server_start.py",
    "app.py",  # ParsPack PaaS entry point
    "hooperzone",
    "accounts",
    "cart",
    "favorites",
    "orders",
    "products",
    "reviews",
    "frontend/dist",
]
SKIP_DIRS = {"__pycache__", "media", "tests", "logs"}
SKIP_SUFFIXES = {".pyc", ".sqlite3"}


def files_to_pack():
    for entry in INCLUDE:
        path = ROOT / entry
        if path.is_file():
            yield path
            continue
        for file in sorted(path.rglob("*")):
            rel_parts = file.relative_to(ROOT).parts
            if file.is_file() and not SKIP_DIRS.intersection(rel_parts) and file.suffix not in SKIP_SUFFIXES:
                yield file


def main():
    if "--dir" not in sys.argv:
        raise SystemExit("Usage: python scripts/build_release.py [--no-build] --dir OUT")
    if "--no-build" not in sys.argv:
        if not (FRONTEND / "node_modules").exists():
            subprocess.run([NPM, "install"], cwd=FRONTEND, check=True)
        subprocess.run([NPM, "run", "build:django"], cwd=FRONTEND, check=True)
    if not (FRONTEND / "dist" / "index.html").exists():
        raise SystemExit("frontend/dist is missing: run without --no-build.")

    out_dir = Path(sys.argv[sys.argv.index("--dir") + 1]).resolve()
    shutil.rmtree(out_dir, ignore_errors=True)
    files = list(files_to_pack())
    for file in files:
        target = out_dir / file.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
    print(f"Copied {len(files)} files into {out_dir}")


if __name__ == "__main__":
    main()
