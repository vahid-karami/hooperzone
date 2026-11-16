"""ParsPack PaaS: server data lives under DATA_DIR (the permanent disk), not in the code folder."""
import importlib
import subprocess
import sys
from pathlib import Path

import wispbyte_start

ROOT = Path(__file__).resolve().parents[2]


def test_env_file_is_created_under_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(wispbyte_start, "DATA_DIR", tmp_path / "disk")
    monkeypatch.setattr(wispbyte_start, "ENV_FILE", tmp_path / "disk" / ".env")
    monkeypatch.delenv("SERVER_IP", raising=False)
    wispbyte_start.ensure_env_file()
    assert "SECRET_KEY=" in (tmp_path / "disk" / ".env").read_text(encoding="utf-8")


def test_production_settings_put_data_under_data_dir(tmp_path):
    code = (
        "from django.conf import settings as s;"
        "print(s.DATABASES['default']['NAME']);print(s.MEDIA_ROOT);print(s.LOG_DIR)"
    )
    env = {
        "DJANGO_SETTINGS_MODULE": "hooperzone.settings.production",
        "SECRET_KEY": "test-only-not-secret",
        "DATA_DIR": str(tmp_path),
        "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", ""),
    }
    out = subprocess.run(
        [sys.executable, "-c", "import django;django.setup();" + code],
        cwd=ROOT, env=env, capture_output=True, text=True, check=True,
    ).stdout.split()
    assert [Path(p) for p in out] == [tmp_path / "database" / "db.sqlite3", tmp_path / "media", tmp_path / "logs"]


def test_app_py_defaults_to_port_8000(monkeypatch):
    monkeypatch.setenv("SERVER_PORT", "1")  # recorded, so teardown removes what app.py sets
    monkeypatch.delenv("SERVER_PORT")
    import app

    importlib.reload(app)
    assert __import__("os").environ["SERVER_PORT"] == "8000"
