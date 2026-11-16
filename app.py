"""Start HooperZone on ParsPack PaaS (Python s2i image, which runs app.py when it exists).

Runs server_start.main(): migrate, collectstatic, seed data once, then Waitress on
port 8000. Set these in the ParsPack panel (Config/Secret or the app's variables):

    DATA_DIR=/data                  # the permanent disk: .env, database/, media/, logs/
    ALLOWED_HOSTS=hooperzone.ir,www.hooperzone.ir,hooperzone.apps.teh11.abrhapaas.com
    CSRF_TRUSTED_ORIGINS=https://hooperzone.ir,https://www.hooperzone.ir,https://hooperzone.apps.teh11.abrhapaas.com

ParsPack builds new versions from the `deploy` branch itself (GitHub webhook).
"""
import os

os.environ.setdefault("SERVER_PORT", "8000")

if __name__ == "__main__":
    import server_start

    server_start.main()
