# HooperZone (هوپرزون)

Persian-first online store for sports and medical supports: knee braces, ankle and wrist supports,
back belts and compression wear. The backend is Django REST and the frontend is a React SPA. Live
at [hooperzone.ir](https://hooperzone.ir).

## Stack

- **Backend:** Python 3.12+, Django 6, Django REST Framework, simplejwt, Pillow, SQLite.
  Production serves it with Waitress + WhiteNoise.
- **Frontend:** React 19, Vite, React Router, react-i18next (Persian RTL and English), vitest, oxlint.
- **Integrations:** ZarinPal (payments, REST v4), SMS.ir (login codes), Enamad/Samandehi badges.

## Quick start

```bash
python scripts/dev.py            # first run: venv, npm packages, migrations, demo data; then starts both servers
python scripts/dev.py backend    # or just one of them
```

Or by hand:

```bash
python -m venv venv && venv/bin/pip install -r requirements.txt   # Windows: venv\Scripts\...
venv/bin/python manage.py migrate
venv/bin/python manage.py seed_demo_store      # demo catalogue (also: seed_sports, seed_category_images)
venv/bin/python manage.py runserver 8001
cd frontend && npm install && npm run dev      # http://localhost:5173 (proxies /api and /media to :8001)
```

Copy `example.env` to `.env` for local settings. In development, OTP codes are returned in the API
response and the payment gateway falls back to a mock when the ZarinPal sandbox is unreachable.

## Tests and checks

```bash
venv/bin/python -m pytest          # backend
cd frontend && npm test            # vitest
cd frontend && npm run lint        # oxlint
```

## What's in it

**Storefront**
- Catalogue browsing by category, body part and sport, with search, filters and quick view.
  Product pages have size guides and reviews.
- Cart, then checkout with a choice of Post (registered), Post Pishtaz or Tipax, then payment on
  ZarinPal.
- Accounts: password login or SMS code, plus profile, order history, tracking codes and favourites.
- Info pages for About, Contact, FAQ, Shipping, Returns, Terms and Privacy. Enamad requires these.

**Admin portal** (`/admin-portal`, staff only)
- Dashboard: revenue over 7, 30 or 90 days, average order, best sellers, low stock.
- Orders: filters, status workflow (forward only), bulk status, tracking codes, printable
  invoice and shipping label, CSV export.
- Products: create and edit, image upload (WebP thumbnails are generated), bulk actions, inline
  stock edits, SEO title and description, CSV export, and a bulk price change ("price list").
- Categories with images; a customers list with CSV export.
- Store settings: shipping fees, unpaid-order timeout, contact details, Enamad/Samandehi codes.

Django admin (`/admin/`) is still available for everything else.

**Housekeeping**
- Unpaid orders are cancelled after a configurable timeout and their stock is released
  (`manage.py cancel_unpaid_orders`). The web app also runs this sweep itself.
- `manage.py backup_db` keeps daily SQLite copies in `database/backups/` and runs on every boot.
- `manage.py build_thumbnails` creates missing product thumbnails.

**SEO**
- Django renders each page's title, description, canonical link, Open Graph tags and JSON-LD
  (Product, BreadcrumbList, OnlineStore) into the HTML. Unknown URLs return a real 404.
- `/robots.txt` and `/sitemap.xml` (with product images).

## Configuration

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` | Django basics |
| `SITE_URL` | Public URL used for canonical links and the sitemap (`https://hooperzone.ir`) |
| `PAYMENT_SANDBOX`, `ZARINPAL_MERCHANT_ID` | ZarinPal sandbox or live mode, and the merchant ID |
| `SMSIR_API_KEY`, `SMSIR_TEMPLATE_ID` | SMS.ir verify template (with a `CODE` parameter) for OTP codes |
| `OTP_RETURN_IN_RESPONSE` | Development only: show OTP codes in the API response (always off in production) |
| `OTP_THROTTLE_RATE`, `AUTH_THROTTLE_RATE` | Per-IP limits for OTP and password endpoints (default `10/min`) |
| `SECURE_COOKIES`, `SECURE_HSTS_SECONDS` | Production cookie and HSTS settings |

Shop-level settings (shipping fees, contact info and so on) live in the database and are edited in
**Admin portal → Store settings**.

## Deployment

See [DEPLOY_WISPBYTE.md](DEPLOY_WISPBYTE.md) for building the upload zip, the server and domain
setup, the ZarinPal, SMS.ir and Enamad steps, and the launch checklist.

## Repository layout

```
accounts/    users (phone login), OTP, SMS.ir client, customer admin API
products/    categories, sports, products, images and thumbnails, product admin API
cart/  favorites/  reviews/
orders/      orders, payments (ZarinPal/IDPay), shop settings, staff admin API, housekeeping commands
hooperzone/  settings, URLs, SEO (seo.py), throttling, CSV helper, tests
frontend/    React app (src/pages, src/components, src/styles, src/i18n/locales)
scripts/     dev.py (local), package_wispbyte.py (deploy zip)
```
