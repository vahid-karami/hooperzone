"""One-time move of a shop's data (database, uploads, .env) onto this server.

Used when moving hosts (Wispbyte -> ParsPack PaaS). Download an archive of `database/`, `media/`
and `.env` from the old server's file manager, then upload it at /import-data/.

The page is off unless the IMPORT_TOKEN environment variable is set, and the upload must carry
the same token. Remove IMPORT_TOKEN as soon as the import is done.
"""
import hmac
import shutil
import sqlite3
import tarfile
import tempfile
import zipfile
from contextlib import closing, contextmanager
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.core.management import call_command
from django.db import connections
from django.http import Http404, HttpResponse
from django.utils.html import escape
from django.views.decorators.csrf import csrf_exempt

ALLOWED_TOP = {"database", "media", ".env"}
DB_NAME = "database/db.sqlite3"

PAGE = """<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>انتقال اطلاعات</title><style>
body{{font-family:Tahoma,sans-serif;max-width:560px;margin:40px auto;padding:0 16px}}
label,input,button{{display:block;margin:10px 0;width:100%}}
button{{padding:10px}}.msg{{padding:10px;background:#e8eef7}}</style>
</head><body><h1>انتقال اطلاعات فروشگاه</h1>
<p>فایل پشتیبان (zip یا tar.gz) شامل پوشه‌های database و media و فایل ‎.env را انتخاب کنید.
اطلاعات فعلی این سرور جایگزین می‌شود.</p>{message}
<form method="post" enctype="multipart/form-data">
<label>کد انتقال (IMPORT_TOKEN)<input type="password" name="token" required autocomplete="off"></label>
<label>فایل پشتیبان<input type="file" name="archive" accept=".zip,.gz,.tgz,.tar" required></label>
<button type="submit">انتقال اطلاعات</button></form></body></html>"""


def _data_dir():
    return Path(getattr(settings, "DATA_DIR", settings.BASE_DIR.parent))


def _safe_rel(name):
    """Relative path inside the data folder, or None for anything outside database/, media/, .env."""
    parts = [p for p in PurePosixPath(name.replace("\\", "/")).parts if p not in ("", ".", "/")]
    # Archives of a whole folder ("server/database/...") are fine: start at the first known top folder.
    for i, part in enumerate(parts):
        if part in ALLOWED_TOP:
            parts = parts[i:]
            break
    else:
        return None
    if ".." in parts or (parts[0] == ".env" and len(parts) != 1) or (parts[0] != ".env" and len(parts) < 2):
        return None
    rel = "/".join(parts)
    if rel.startswith("database/backups/") or rel.endswith(("-wal", "-shm", "-journal")):
        return None  # old backups and SQLite side files are not needed
    return rel


@contextmanager
def _open_members(path):
    """Yield an iterator of (name, open binary file) for regular files in a zip or tar(.gz)."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            yield ((i.filename, lambda i=i: zf.open(i)) for i in zf.infolist() if not i.is_dir())
        return
    try:
        tf = tarfile.open(path, mode="r:*")
    except tarfile.TarError as e:
        raise ValueError("The file is not a zip or tar.gz archive.") from e
    with tf:
        # Only regular files: symlinks, devices and folders are skipped.
        yield ((i.name, lambda i=i: tf.extractfile(i)) for i in tf.getmembers() if i.isfile())


def import_archive(archive_path, data_dir):
    """Replace data_dir's database, media and .env with the archive's. Returns a summary."""
    data_dir = Path(data_dir)
    with tempfile.TemporaryDirectory() as tmp:
        staging = Path(tmp) / "data"
        counts = {"files": 0, "media": 0, "env": False}
        with _open_members(archive_path) as members:
            for name, opener in members:
                rel = _safe_rel(name)
                if not rel:
                    continue
                target = staging / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                with opener() as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                counts["files"] += 1
                counts["media"] += rel.startswith("media/")
                counts["env"] = counts["env"] or rel == ".env"

        db = staging / DB_NAME
        if not db.exists():
            raise ValueError(f"The archive has no {DB_NAME}.")
        try:
            with closing(sqlite3.connect(db)) as conn:  # closing(): `with conn` alone leaves it open
                ok = conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        except sqlite3.DatabaseError:
            ok = False
        if not ok:
            raise ValueError(f"{DB_NAME} is not a valid SQLite database.")

        connections.close_all()
        (data_dir / "database").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(db, data_dir / DB_NAME)
        if (staging / "media").exists():
            shutil.rmtree(data_dir / "media", ignore_errors=True)
            shutil.copytree(staging / "media", data_dir / "media")
        if counts["env"]:
            shutil.copyfile(staging / ".env", data_dir / ".env")
    call_command("migrate", interactive=False, verbosity=0)
    return counts


@csrf_exempt  # the token is the protection; there is no session on this page
def import_data(request):
    token = getattr(settings, "IMPORT_TOKEN", "")
    if not token:
        raise Http404()
    message = ""
    status = 200
    if request.method == "POST":
        given = request.POST.get("token", "")
        upload = request.FILES.get("archive")
        if not hmac.compare_digest(given.encode(), token.encode()):
            message, status = '<p class="msg">کد انتقال درست نیست.</p>', 403
        elif not upload:
            message = '<p class="msg">فایلی انتخاب نشده است.</p>'
        else:
            with tempfile.NamedTemporaryFile(suffix=Path(upload.name).suffix, delete=False) as f:
                for chunk in upload.chunks():
                    f.write(chunk)
            try:
                result = import_archive(f.name, _data_dir())
            except ValueError as e:
                message = f'<p class="msg">انتقال انجام نشد: {escape(str(e))}</p>'
            else:
                message = (
                    f'<p class="msg">انتقال انجام شد: {result["files"]} فایل، {result["media"]} تصویر'
                    f'{"، فایل ‎.env" if result["env"] else ""}. حالا IMPORT_TOKEN را حذف و '
                    "اپلیکیشن را ری‌استارت کنید.</p>"
                )
            finally:
                Path(f.name).unlink(missing_ok=True)
    response = HttpResponse(PAGE.format(message=message), status=status)
    response["Cache-Control"] = "no-store"
    return response
