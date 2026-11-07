import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Copy the SQLite database to database/backups/ (once a day) and keep the newest copies."

    def add_arguments(self, parser):
        parser.add_argument("--keep", type=int, default=7)
        parser.add_argument("--force", action="store_true", help="Back up even if today's copy exists.")
        parser.add_argument("--source", help="Database file to back up (default: the configured database).")

    def handle(self, *args, keep, force, source=None, **options):
        db = settings.DATABASES["default"]
        if not source and "sqlite3" not in db["ENGINE"]:
            self.stdout.write("Not a SQLite database; skipping backup.")
            return
        source = Path(source or db["NAME"])
        if not source.exists():
            self.stdout.write("No database file yet; skipping backup.")
            return

        backups = source.parent / "backups"
        backups.mkdir(exist_ok=True)
        target = backups / f"db-{datetime.now():%Y-%m-%d}.sqlite3"
        if target.exists() and not force:
            self.stdout.write(f"Backup {target.name} already exists.")
        else:
            # The online backup API gives a consistent copy even while the site is writing.
            with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
                src.backup(dst)
            self.stdout.write(f"Backed up the database to {target}.")

        for old in sorted(backups.glob("db-*.sqlite3"), reverse=True)[keep:]:
            old.unlink()
