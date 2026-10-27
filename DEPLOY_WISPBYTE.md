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
and restart the server after each change. An `.env` created by an older version may still have
`PAYMENT_SANDBOX=True` and `OTP_RETURN_IN_RESPONSE=True`: change the first as below. The second is
ignored in production now (codes are never shown on screen), so you can delete it.

| Variable | Value |
| --- | --- |
| `ALLOWED_HOSTS` | `hooperzone.ir,www.hooperzone.ir` (plus the server IP while testing) |
| `CSRF_TRUSTED_ORIGINS` | `https://hooperzone.ir,https://www.hooperzone.ir` |
| `SITE_URL` | `https://hooperzone.ir`. Used for canonical links, the sitemap and share previews. |
| `SECURE_COOKIES` | `True`. Set it to `False` only to use `/admin/` over plain `http://IP:port`. |
| `PAYMENT_SANDBOX` | `False` for real payments. `True` sends customers to ZarinPal's sandbox (no money is taken). |
| `ZARINPAL_MERCHANT_ID` | The 36-character merchant ID from your ZarinPal panel. Without it customers can't pay. |
| `SMSIR_API_KEY`, `SMSIR_TEMPLATE_ID` | SMS.ir API key and verify-template ID for login codes (see section 5). Without them, SMS login and registration don't work; password login still does. |
| `SECURE_HSTS_SECONDS` | `0` at first. Once `https://hooperzone.ir` works everywhere, set `31536000`. |
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
   plain HTTP. Then turn on **SSL/TLS → Edge Certificates → Always Use HTTPS**. Visitors still
   get HTTPS; only the hop from Cloudflare to Wispbyte is plain HTTP.
6. Open `https://hooperzone.ir` and `https://hooperzone.ir/admin/`.

## 5. Payments, SMS and Enamad (before taking real orders)

**ZarinPal**
1. Sign up at [zarinpal.com](https://www.zarinpal.com), add a *website gateway* (درگاه پرداخت) for
   `hooperzone.ir` and complete the identity and bank-account (Sheba) steps.
2. ZarinPal approves gateways for sites that have the legal pages (already in the site footer:
   About, Contact, Terms, Privacy, Returns) and, usually, an Enamad badge.
3. Copy the merchant ID into `ZARINPAL_MERCHANT_ID`, set `PAYMENT_SANDBOX=False` and restart.
   The console logs a warning while the merchant ID is missing.
4. Make a small real order and check that it shows as paid with a ZarinPal reference in
   **Admin portal → Orders**.

**SMS.ir (login codes)**
1. Sign up at [sms.ir](https://sms.ir) and top up credit.
2. **Developers → API keys**: create a key → `SMSIR_API_KEY`.
3. **Developers → Verify templates**: create a template such as
   `کد ورود شما به هوپرزون: #CODE#`. The parameter must be named `CODE`. Once it is approved, put
   its ID in `SMSIR_TEMPLATE_ID`.
4. Restart and test **Login → SMS code** with your own phone.

**Enamad (اینماد)**
1. Apply at [enamad.ir](https://enamad.ir) with the domain, your national ID and a business
   address/phone. Fill in the same phone, email and address in **Admin portal → Store settings**:
   the Contact page and footer show them, and Enamad checks them.
2. Enamad asks you to put a verification code on the site. When the badge is issued, paste its
   HTML in **Store settings → Enamad code**; it appears in the footer. Do the same for Samandehi.

## 6. Launch checklist

- [ ] `.env`: `PAYMENT_SANDBOX=False`, `ZARINPAL_MERCHANT_ID`, `SMSIR_API_KEY`, `SMSIR_TEMPLATE_ID`, `SITE_URL`.
- [ ] **Admin portal → Store settings**: shipping fees for Post, Pishtaz and Tipax, store phone,
      email, address, Instagram/Telegram, unpaid-order timeout.
- [ ] Replace the demo catalogue: in **Admin portal → Products**, select the demo products and
      delete or deactivate them, then add your own products and photos (the product dialog uploads
      images directly; each one gets a fast-loading thumbnail automatically).
- [ ] Review the wording of the Terms, Returns and Privacy pages
      (`frontend/src/i18n/locales/fa.json` → `info`) and adjust to your actual policy.
- [ ] Place a real test order end to end, print its invoice, add a tracking code, and check the
      customer sees it under **My orders**.
- [ ] Google: add `hooperzone.ir` in [Search Console](https://search.google.com/search-console),
      verify with a DNS TXT record in Cloudflare, and submit `https://hooperzone.ir/sitemap.xml`.
      Do the same in Bing Webmaster Tools.
- [ ] Check a product link preview by pasting a product URL into Telegram.

## Every later deploy

```bash
python scripts/package_wispbyte.py
```

Upload the new zip in **Files**, unarchive it (overwrite), delete the zip and **Restart**.
Migrations run automatically on boot.

## Backups and housekeeping

Every boot runs `backup_db`, which copies the database to `database/backups/db-YYYY-MM-DD.sqlite3`
(once a day, keeping the last 7). Those copies are on the same server, so still download
`database/` and the `media/` folder from **Files** regularly. They hold all orders, users and
uploaded photos, and a free server can be deleted if it's inactive.

Unpaid orders are cancelled automatically after the timeout in Store settings, and their stock is
released. Errors and payment problems are logged to `logs/django.log`.
