# Deploying HooperZone on ParsPack PaaS (Iran)

Hosting inside Iran so the shop opens without a VPN. ParsPack PaaS app `hooperzone-django`
(project `hooperzone`, datacenter Tehran11), address `https://hooperzone.apps.teh11.abrhapaas.com`.

## How it runs
- Code: public GitHub repo `vahid-karami/hooperzone`, branch **`deploy`** (built by CI from
  `master`, includes the built React app). ParsPack's Python 3.12 image installs
  `requirements.txt` and runs **`app.py`**, which runs the same boot as Wispbyte
  (`wispbyte_start.main()`: migrate, collectstatic, seeds) and serves Waitress on port **8000**.
- Resources: 0.5 vCPU, 512 MB RAM, 1 GB disk `data` mounted at **`/data`**.
- Everything that must survive a rebuild lives on `/data`: `.env`, `database/`, `media/`, `logs/`.
  Files anywhere else are lost on every restart.

## Environment variables (panel → متغیرهای محیطی)
| Name | Value |
|---|---|
| `DATA_DIR` | `/data` |
| `ALLOWED_HOSTS` | `hooperzone.ir,www.hooperzone.ir,hooperzone.apps.teh11.abrhapaas.com,localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | `https://hooperzone.ir,https://www.hooperzone.ir,https://hooperzone.apps.teh11.abrhapaas.com` |
| `IMPORT_TOKEN` | only while moving data (see below); delete afterwards |

Panel variables win over `/data/.env` (python-dotenv never overrides). Secrets such as
`SECRET_KEY`, `SMSIR_*` and `ZARINPAL_MERCHANT_ID` live in `/data/.env`.

## New versions
Push to `master` → CI publishes `deploy`. To build it on ParsPack either open
ویرایش منبع کد and save the same repo/branch (rebuilds now), or add the panel's وب‌هوک URL
to GitHub (repo Settings → Webhooks → Payload URL, content type JSON, no secret) so every push
to `deploy` rebuilds automatically.

## Moving data from another server (one time)
1. Old server's file manager: archive `database/`, `media/` and `.env` (zip or tar.gz) and download it.
2. ParsPack: add `IMPORT_TOKEN` = any random text of 20+ characters; wait for the restart.
3. Open `https://hooperzone.apps.teh11.abrhapaas.com/import-data/`, enter the same token,
   pick the archive and send. The database, photos and `.env` on `/data` are replaced and
   migrations run.
4. Delete `IMPORT_TOKEN` in the panel (the page then returns 404) and restart (پاور کنترل).

## Domain
Panel → تنظیمات دامنه و IP: add `hooperzone.ir` and `www.hooperzone.ir`, then point DNS at
the app as the panel says, **without** Cloudflare's proxy (grey cloud), since Cloudflare's
addresses are often blocked in Iran.
