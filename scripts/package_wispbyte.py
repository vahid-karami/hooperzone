"""Build the React app and pack everything Wispbyte needs into one zip. See DEPLOY_WISPBYTE.md.

    python scripts/package_wispbyte.py              # build frontend + zip
    python scripts/package_wispbyte.py --no-build   # zip the existing frontend/dist
    python scripts/package_wispbyte.py --dir OUT    # copy the bundle into folder OUT instead (CI)

Output: build/hooperzone-wispbyte.zip. Upload it in the Wispbyte file manager and unarchive it
in /home/container. It never contains .env, database/ or media/, so redeploys keep live data.
CI uses --dir to publish the same files on the `deploy` branch for auto-deploy.
"""
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
OUT = ROOT / "build" / "hooperzone-wispbyte.zip"
NPM = shutil.which("npm.cmd") or shutil.which("npm") or "npm"

INCLUDE = [
    "manage.py",
    "requirements.txt",
    "wispbyte_start.py",
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
    if "--no-build" not in sys.argv:
        if not (FRONTEND / "node_modules").exists():
            subprocess.run([NPM, "install"], cwd=FRONTEND, check=True)
        subprocess.run([NPM, "run", "build:django"], cwd=FRONTEND, check=True)
    if not (FRONTEND / "dist" / "index.html").exists():
        raise SystemExit("frontend/dist is missing: run without --no-build.")

    if "--dir" in sys.argv:
        out_dir = Path(sys.argv[sys.argv.index("--dir") + 1]).resolve()
        shutil.rmtree(out_dir, ignore_errors=True)
        files = list(files_to_pack())
        for file in files:
            target = out_dir / file.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, target)
        print(f"Copied {len(files)} files into {out_dir}")
        return

    OUT.parent.mkdir(exist_ok=True)
    count = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in files_to_pack():
            zf.write(file, file.relative_to(ROOT).as_posix())
            count += 1
    print(f"Packed {count} files into {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
