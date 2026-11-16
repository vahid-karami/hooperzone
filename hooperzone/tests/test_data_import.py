"""/import-data/: one-time move of database, media and .env onto a new server."""
import io
import sqlite3
import tarfile
import zipfile
from contextlib import closing

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from hooperzone import data_import

TOKEN = "t" * 32


def sqlite_bytes(tmp_path):
    db = tmp_path / "src.sqlite3"
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("create table shop (name text)")
        conn.execute("insert into shop values ('hooperzone')")
        conn.commit()
    return db.read_bytes()


def make_zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def make_tgz(files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))
    return buf.getvalue()


@pytest.fixture
def data_dir(tmp_path, settings, monkeypatch):
    target = tmp_path / "disk"
    (target / "media" / "old").mkdir(parents=True)
    (target / "media" / "old" / "stale.jpg").write_bytes(b"stale")
    settings.DATA_DIR = target
    settings.IMPORT_TOKEN = TOKEN
    monkeypatch.setattr(data_import, "call_command", lambda *a, **k: None)  # no migrate on the fake DB
    return target


def post(client, archive, name="backup.zip", token=TOKEN):
    return client.post("/import-data/", {"token": token, "archive": SimpleUploadedFile(name, archive)})


def test_page_is_off_without_token(client, settings):
    settings.IMPORT_TOKEN = ""
    assert client.get("/import-data/").status_code == 404
    assert client.post("/import-data/", {"token": ""}).status_code == 404


def test_wrong_token_is_refused(client, data_dir, tmp_path):
    archive = make_zip({"database/db.sqlite3": sqlite_bytes(tmp_path)})
    response = post(client, archive, token="x" * 32)
    assert response.status_code == 403
    assert not (data_dir / "database" / "db.sqlite3").exists()


@pytest.mark.django_db
def test_zip_import_replaces_database_media_and_env(client, data_dir, tmp_path):
    archive = make_zip({
        "database/db.sqlite3": sqlite_bytes(tmp_path),
        "database/backups/db-old.sqlite3": b"old backup",
        "media/products/a.jpg": b"photo",
        ".env": b"SECRET_KEY=moved",
        "server_start.py": b"code is ignored",
    })
    response = post(client, archive)
    assert response.status_code == 200
    assert "انتقال انجام شد" in response.content.decode()
    with closing(sqlite3.connect(data_dir / "database" / "db.sqlite3")) as conn:
        assert conn.execute("select name from shop").fetchone()[0] == "hooperzone"
    assert (data_dir / "media" / "products" / "a.jpg").read_bytes() == b"photo"
    assert not (data_dir / "media" / "old").exists()  # media is replaced, not merged
    assert (data_dir / ".env").read_text() == "SECRET_KEY=moved"
    assert not (data_dir / "database" / "backups").exists()
    assert not (data_dir / "server_start.py").exists()


@pytest.mark.django_db
def test_tar_gz_from_a_wrapping_folder_works(client, data_dir, tmp_path):
    archive = make_tgz({
        "server/database/db.sqlite3": sqlite_bytes(tmp_path),
        "server/media/sports/b.webp": b"img",
    })
    assert post(client, archive, name="backup.tar.gz").status_code == 200
    assert (data_dir / "media" / "sports" / "b.webp").read_bytes() == b"img"


def test_path_traversal_and_bad_database_are_rejected(client, data_dir, tmp_path):
    archive = make_zip({
        "database/db.sqlite3": b"not sqlite",
        "media/../../evil.txt": b"x",
    })
    response = post(client, archive)
    assert "انتقال انجام نشد" in response.content.decode()
    assert not (tmp_path / "evil.txt").exists()
    assert not (data_dir / "database" / "db.sqlite3").exists()


def test_safe_rel_rules():
    assert data_import._safe_rel("media/a/b.jpg") == "media/a/b.jpg"
    assert data_import._safe_rel("x/.env") == ".env"
    assert data_import._safe_rel("media/../etc/passwd") is None
    assert data_import._safe_rel(".env/inner") is None
    assert data_import._safe_rel("manage.py") is None
    assert data_import._safe_rel("database/db.sqlite3-wal") is None
