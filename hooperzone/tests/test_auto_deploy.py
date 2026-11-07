import io
import zipfile

import pytest

import wispbyte_start


def release_zip(files, prefix="hooperzone-deploy/"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(prefix, "")
        for name, content in files.items():
            zf.writestr(prefix + name, content)
    return buf.getvalue()


RELEASE = {
    "wispbyte_start.py": "new start",
    "manage.py": "new manage",
    "frontend/dist/index.html": "<html>new</html>",
    "frontend/dist/assets/app-new.js": "js",
    "DEPLOY_VERSION": "abc1234def\n",
    ".env": "SECRET_KEY=from-release",
    "database/db.sqlite3": "release db",
    "media/x.jpg": "release media",
}


def test_install_release_keeps_server_data(tmp_path):
    (tmp_path / ".env").write_text("SECRET_KEY=live")
    (tmp_path / "database").mkdir()
    (tmp_path / "database" / "db.sqlite3").write_text("live db")
    (tmp_path / "media").mkdir()
    (tmp_path / "media" / "x.jpg").write_text("live photo")
    (tmp_path / "frontend" / "dist" / "assets").mkdir(parents=True)
    (tmp_path / "frontend" / "dist" / "assets" / "app-old.js").write_text("old")

    version = wispbyte_start.install_release(release_zip(RELEASE), root=tmp_path)

    assert version == "abc1234def"
    assert (tmp_path / "manage.py").read_text() == "new manage"
    assert (tmp_path / "frontend" / "dist" / "assets" / "app-new.js").exists()
    assert not (tmp_path / "frontend" / "dist" / "assets" / "app-old.js").exists()
    assert (tmp_path / ".env").read_text() == "SECRET_KEY=live"
    assert (tmp_path / "database" / "db.sqlite3").read_text() == "live db"
    assert (tmp_path / "media" / "x.jpg").read_text() == "live photo"


def test_install_release_rejects_an_incomplete_bundle(tmp_path):
    (tmp_path / "manage.py").write_text("live")
    with pytest.raises(ValueError):
        wispbyte_start.install_release(release_zip({"manage.py": "x"}), root=tmp_path)
    assert (tmp_path / "manage.py").read_text() == "live"


def test_auto_deploy_only_runs_on_the_wispbyte_server(monkeypatch, tmp_path):
    monkeypatch.setattr(wispbyte_start, "ROOT", tmp_path)
    monkeypatch.delenv("AUTO_DEPLOY", raising=False)
    monkeypatch.delenv("P_SERVER_UUID", raising=False)
    assert wispbyte_start.auto_deploy_settings() is None  # a PC

    monkeypatch.setenv("P_SERVER_UUID", "867ae234")
    assert wispbyte_start.auto_deploy_settings() == ("vahid-karami/hooperzone", "deploy", 300)

    monkeypatch.setenv("AUTO_DEPLOY", "False")
    assert wispbyte_start.auto_deploy_settings() is None  # switched off in .env

    monkeypatch.setenv("AUTO_DEPLOY", "true")
    (tmp_path / ".git").mkdir()
    assert wispbyte_start.auto_deploy_settings() is None  # never overwrite a git checkout
