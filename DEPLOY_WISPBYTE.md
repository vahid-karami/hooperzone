# Deploying HooperZone to Wispbyte (free) with hooperzone.ir

One Python process serves everything: the API (`/api/...`), Django admin (`/admin/`), the built
React site (every other URL), `/static` (WhiteNoise) and `/media` (Django). Wispbyte gives the
server an `IP:port`; Cloudflare (free) puts `https://hooperzone.ir` in front of it.

Files involved: `wispbyte_start.py`, `scripts/package_wispbyte.py`,
`hooperzone/settings/production.py`, `requirements.txt`.

Free plan limits: 1 server, about 512 MB RAM and 1 GB disk. In a local test the app used about 65 MB
of RAM and about 110 MB of disk including its Python packages, so the free plan is enough for a demo shop.

## 1. Build the upload zip (your PC)

```bash
python scripts/package_wispbyte.py
```

This builds React (`npm run build:django`) and writes `build/hooperzone-wispbyte.zip`. The zip
never contains `.env`, `database/` or `media/`, so uploading a new one keeps live data.

## 2. Create the server (Wispbyte panel)

1. **Create server** → type **Python**. Pick the free plan.
2. Open the server → **Startup**:
   - **Docker image / Python version**: 3.12 or newer (Django 6 needs at least 3.12).
   - **App py file**: `wispbyte_start.py`
   - **Requirements file**: `requirements.txt`
   - Leave the Git repo address empty (the zip contains the built frontend; git does not).
3. **Files** → upload `hooperzone-wispbyte.zip` into `/home/container` → right-click →
   **Unarchive** → delete the zip.
4. **Console** → **Start**. The first boot installs packages, then you should see migrations,
   the demo catalogue loading and `HooperZone is running on port <port>`.
5. **Network** shows the address, e.g. `123.45.67.89:25565`. Open `http://123.45.67.89:25565`.
   If you get *Bad Request (400)*, add that IP to `ALLOWED_HOSTS` in `.env` and restart.

## 3. Settings (`.env`)

The first boot creates `/home/container/.env` with a random `SECRET_KEY`. Edit it in **Files**
and restart the server after each change.

| Variable | Value |
| --- | --- |
| `ALLOWED_HOSTS` | `hooperzone.ir,www.hooperzone.ir` (plus the server IP while testing) |
| `CSRF_TRUSTED_ORIGINS` | `https://hooperzone.ir,https://www.hooperzone.ir` |
| `SECURE_COOKIES` | `True`. Set it to `False` only to use `/admin/` over plain `http://IP:port`. |
| `PAYMENT_SANDBOX` | `True` = fake payment gateway (demo). `False` once a real gateway is set up. |
| `OTP_RETURN_IN_RESPONSE` | `True` shows the SMS code on screen (no SMS provider yet), so anyone can log in to any phone number. Set it to `False` before real customers use the site. |
| `ADMIN_PHONE`, `ADMIN_PASSWORD` | Fill in, restart once to create the Django admin user, then delete `ADMIN_PASSWORD`. |

Never put `.env` in git, and never change `SECRET_KEY` (it signs everyone's login tokens).

## 4. Domain hooperzone.ir

1. Register `hooperzone.ir` at [nic.ir](https://nic.ir) or an IRNIC reseller. IRNIC asks for a
   NIC handle (Iranian ID details), which you have to enter yourself.
2. Create a free [Cloudflare](https://dash.cloudflare.com) account → **Add a domain** →
   `hooperzone.ir`. Cloudflare gives you two nameservers; set them as the domain's DNS servers
   in your IRNIC / reseller panel. This can take a few hours.
3. In Cloudflare **DNS**, add these records (proxied, orange cloud):
   - `A` record, name `@`, value the Wispbyte server IP
   - `CNAME` record, name `www`, target `hooperzone.ir`

   If Wispbyte shows a hostname instead of an IP, use a `CNAME` to that hostname for `@`.
4. **Rules → Origin Rules → Create rule**: when *Hostname* is `hooperzone.ir` or
   `www.hooperzone.ir`, **Destination port → rewrite to** the Wispbyte port (e.g. `25565`).
   Cloudflare normally only connects to port 80, and this rule sends visitors to your server's
   port instead.
5. **SSL/TLS → Overview**: set the mode to **Flexible**, because the Wispbyte server only speaks
   plain HTTP. Then turn on **SSL/TLS → Edge Certificates → Always Use HTTPS**.
6. Open `https://hooperzone.ir` and `https://hooperzone.ir/admin/`.

## Every later deploy

```bash
python scripts/package_wispbyte.py
```

Upload the new zip in **Files**, unarchive it (overwrite), delete the zip and **Restart**.
Migrations run automatically on boot.

## Backups

Download `database/db.sqlite3` and the `media/` folder from **Files** now and then. They hold
all orders, users and uploaded photos, and a free server can be deleted if it's inactive.
