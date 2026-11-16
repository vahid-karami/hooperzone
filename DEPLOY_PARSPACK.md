# Deploying HooperZone on ParsPack PaaS (Iran)

The shop is hosted inside Iran so it opens without a VPN. One Python process serves everything:
the API (`/api/...`), Django admin (`/admin/`), the built React site (every other URL), `/static`
(WhiteNoise) and `/media` (Django).

ParsPack PaaS app `hooperzone-django` (project `hooperzone`, datacenter Tehran11). Default address
`https://hooperzone.apps.teh11.abrhapaas.com`; live at `https://hooperzone.ir`.

Files involved: `app.py`, `server_start.py`, `scripts/build_release.py`,
`hooperzone/settings/production.py`, `requirements.txt`, `.github/workflows/ci-cd.yml`.

## How it runs
- Code: public GitHub repo `vahid-karami/hooperzone`, branch **`deploy`** (built by CI from
  `master`, includes the built React app). ParsPack's Python 3.12 image installs
  `requirements.txt` and runs **`app.py`**, which calls `server_start.main()`: migrate,
  collectstatic, the seed commands, then Waitress on port **8000**.
- Resources: 0.5 vCPU, 512 MB RAM, 1 GB disk `data` mounted at **`/data`**. Billing is hourly
  from the ParsPack wallet (about 450 toman/hour); keep it topped up or the app stops.
- Everything that must survive a rebuild lives on `/data`: `.env`, `database/`, `media/`, `logs/`.
  Files anywhere else are lost on every restart.

## Settings
Panel → app → متغیرهای محیطی (environment variables). Panel variables win over `/data/.env`
(python-dotenv never overrides), and a change restarts the app.

| Name | Value |
|---|---|
| `DATA_DIR` | `/data` |
| `ALLOWED_HOSTS` | `hooperzone.ir,www.hooperzone.ir,hooperzone.apps.teh11.abrhapaas.com,localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | `https://hooperzone.ir,https://www.hooperzone.ir,https://hooperzone.apps.teh11.abrhapaas.com` |
| `IMPORT_TOKEN` | only while moving data (see below); delete afterwards |

Secrets live in `/data/.env` (created on first boot with a random `SECRET_KEY`):

| Variable | Value |
| --- | --- |
| `SITE_URL` | `https://hooperzone.ir`. Used for canonical links, the sitemap and share previews. |
| `SECURE_COOKIES` | `True`. |
| `PAYMENT_SANDBOX` | `False` for real payments. `True` sends customers to ZarinPal's sandbox (no money is taken). |
| `ZARINPAL_MERCHANT_ID` | The 36-character merchant ID from your ZarinPal panel. Without it customers can't pay. |
| `SMSIR_API_KEY`, `SMSIR_TEMPLATE_ID` | SMS.ir API key and verify-template ID for login codes. Without them SMS login and registration don't work; password login still does. |
| `SECURE_HSTS_SECONDS` | `0` at first; `31536000` once https works for both names. |
| `ADMIN_PHONE`, `ADMIN_PASSWORD` | Fill in, restart once to create the Django admin user, then delete `ADMIN_PASSWORD`. |

Never put `.env` in git, and never change `SECRET_KEY` (it signs everyone's login tokens).

## New versions (automatic)
1. Push to `master`. **GitHub Actions** runs the backend and frontend tests, lint and the build;
   a failing push is never deployed.
2. When it passes, CI copies the ready-to-run files (`scripts/build_release.py`) to the **`deploy`**
   branch, with the commit id in `DEPLOY_VERSION`.
3. A GitHub webhook (repo Settings → Webhooks, the URL from the panel's وب‌هوک page) tells
   ParsPack, which builds and starts the new version. The site may answer slowly for a moment.

To rebuild by hand: panel → ویرایش منبع کد (edit code source) → save the same repo and branch.

**Rolling back:** panel → نسخه ها (versions) → عقبگرد (roll back) on an older version, or revert the
bad commit on `master` (`git revert <id>` and push).

## Domain and HTTPS
DNS for `hooperzone.ir` is at Cloudflare, but **not proxied** (grey cloud, "DNS only"), because
Cloudflare's addresses are often blocked in Iran:

| Type | Name | Content |
|---|---|---|
| A | `hooperzone.ir` | `176.97.218.34` |
| A | `www` | `176.97.218.34` |

Both names are added in panel → تنظیمات دامنه و IP (domain and IP settings) with the free
certificate (Let's Encrypt), which ParsPack renews itself. A new name only gets its certificate
after its DNS points at ParsPack.

Rate limits (login, SMS codes) count per visitor IP, taken from the X-Forwarded-For entry that
ParsPack's ingress adds (`server_start.serve`). If Cloudflare ever proxies the site again (orange
cloud), set `TRUST_CF_CONNECTING_IP=True` so the limits use Cloudflare's visitor-IP header;
never set it while the cloud is grey, because then anyone can forge that header.

## Moving data from another server (one time)
1. On the old server, archive `database/`, `media/` and `.env` (zip or tar.gz) and download it.
2. ParsPack: add `IMPORT_TOKEN` = random text of 20+ characters; wait for the restart.
3. Open `https://hooperzone.ir/import-data/`, enter the same token, pick the archive and send.
   The database, photos and `.env` on `/data` are replaced and migrations run.
4. Delete `IMPORT_TOKEN` in the panel (the page then returns 404) and restart (پاور کنترل).

## Payments, SMS and Enamad
**ZarinPal**
1. Add a *website gateway* (درگاه پرداخت) for `hooperzone.ir` at [zarinpal.com](https://www.zarinpal.com)
   and complete the identity and bank-account (Sheba) steps. ZarinPal wants the legal pages
   (already in the footer) and, usually, an Enamad badge.
2. Put the merchant ID in `ZARINPAL_MERCHANT_ID`, set `PAYMENT_SANDBOX=False`, restart.
3. Make a small real order and check that it shows as paid in **Admin portal → Orders**.

**SMS.ir (login codes)**
1. At [sms.ir](https://sms.ir): **Developers → API keys** → `SMSIR_API_KEY`.
2. **Developers → Verify templates**: e.g. `کد ورود شما به هوپرزون: #CODE#` (the parameter must be
   named `CODE`); once approved, its ID goes in `SMSIR_TEMPLATE_ID`.
3. Restart and test **Login → SMS code** with your own phone.

**Enamad (اینماد)**
1. Apply at [enamad.ir](https://enamad.ir). Use the same phone, email and address as in
   **Admin portal → Store settings** (the Contact page and footer show them).
2. Put verification files in `hooperzone/site_root/` (served at the site root). When the badge
   is issued, paste its HTML in **Store settings → Enamad code**. Same for Samandehi.

## Launch checklist
- [ ] `/data/.env`: `PAYMENT_SANDBOX=False`, `ZARINPAL_MERCHANT_ID`, `SMSIR_API_KEY`, `SMSIR_TEMPLATE_ID`, `SITE_URL`.
- [ ] **Admin portal → Store settings**: shipping fees, store phone, email, address, social links,
      unpaid-order timeout.
- [ ] Review the Terms, Returns and Privacy wording (`frontend/src/i18n/locales/fa.json` → `info`).
- [ ] Place a real test order end to end, print its invoice, add a tracking code, and check the
      customer sees it under **My orders**.
- [ ] Google Search Console and Bing: verify `hooperzone.ir` (DNS TXT record in Cloudflare) and
      submit `https://hooperzone.ir/sitemap.xml`.

## Staff who manage products
The **Product editors** group (created on every boot by `setup_roles`) can add and edit products,
photos, categories and prices in `/admin-portal`, but can't see orders, customers or shop
settings, and can't delete products or categories.
1. The person signs up at `https://hooperzone.ir/register`.
2. `https://hooperzone.ir/admin/` → **Users** → their phone → tick **Staff status**, add the group
   **Product editors**, leave **Superuser status** off, save.
3. They open **پنل مدیریت** from their account menu.

## Backups and housekeeping
Every boot runs `backup_db`, which copies the database to `/data/database/backups/` once a day
(keeping 7). Those copies sit on the same disk, so also turn on panel → مدیریت بکاپ (backup
management) automatic backups. Unpaid orders are cancelled after the Store settings timeout and
their stock is released. Errors and payment problems go to `/data/logs/django.log` and the
panel's لاگ ها (logs).
