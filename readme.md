# HooperZone (هوپرزون)

Persian-first online store for sports and medical supports: knee braces, ankle and wrist supports,
back belts and compression wear. The backend is Django REST and the frontend is a React SPA. Live
at [hooperzone.ir](https://hooperzone.ir).

## Stack

- **Backend:** Python 3.12+, Django 6, Django REST Framework, simplejwt, Pillow, SQLite.
  Production serves it with Waitress + WhiteNoise.
- **Frontend:** React 19, Vite, React Router, react-i18next (Persian RTL and English), vitest, oxlint.
- **Integrations:** ZarinPal (payments, REST v4), SMS.ir (login codes), Enamad/Samandehi badges.

## Installation

### 1. Prerequisites

| Tool | Version | Check with |
| --- | --- | --- |
| Python | 3.12 or newer (Django 6 needs it) | `python --version` |
| Node.js | 20.19+ or 22.12+ (Vite 8 needs it) | `node --version` |
| Git | any recent version | `git --version` |

On Windows, tick **"Add python.exe to PATH"** in the Python installer.

### 2. Get the code

```bash
git clone https://github.com/vahid-karami/hooperzone.git
cd hooperzone
```

### 3. Option A: one command (recommended)

```bash
python scripts/dev.py
```

On the first run this:
1. creates the `venv/` virtualenv and installs `requirements.txt`,
2. runs the database migrations (SQLite, `hooperzone/db.sqlite3`),
3. loads the demo store (categories, products, photos, sports) if the database is empty,
4. installs the frontend's npm packages,
5. starts Django on the first free port from 8000 and Vite on **http://localhost:5173**.

Later runs skip what is already done and just start both servers. Press `Ctrl+C` to stop.
Other modes:

```bash
python scripts/dev.py setup      # set everything up, then exit
python scripts/dev.py backend    # Django only
python scripts/dev.py frontend   # Vite only (start the backend first)
```

### 3. Option B: step by step

**Backend** (from the repo root):

```bash
python -m venv venv
# Windows:      venv\Scripts\activate
# macOS/Linux:  source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_store        # demo catalogue (optional)
python manage.py seed_category_images   # category photos (optional)
python manage.py seed_sports            # sports and their photos (optional)
python manage.py runserver 8001
```

**Frontend** (in a second terminal):

```bash
cd frontend
npm install
```

Create `frontend/.env.local` so Vite sends API calls to your Django port (default is 8000):

```env
VITE_BACKEND_URL=http://localhost:8001
```

Then start it:

```bash
npm run dev       # http://localhost:5173
```

### 4. Settings file (optional for local use)

Local development works without a `.env` file. To change settings, copy the example and edit it:

```bash
cp example.env .env        # Windows: copy example.env .env
```

In development, SMS login codes are shown in the API response (and in the Django console), and
payments use ZarinPal's sandbox, so you can test checkout without real money. See
[Configuration](#configuration) for every variable.

### 5. Create an admin user

```bash
python manage.py createsuperuser        # asks for a phone number and a password
```

Sign in on the site with that phone number and password, then open:
- **http://localhost:5173/admin-portal** for the shop's admin portal (orders, products, settings)
- **http://localhost:8001/admin/** for Django admin (use your backend's port)

### 6. Addresses

| What | URL |
| --- | --- |
| Shop (React) | http://localhost:5173 |
| Admin portal | http://localhost:5173/admin-portal |
| API | http://localhost:8001/api/ |
| Django admin | http://localhost:8001/admin/ |

### Troubleshooting

- **Port already in use:** `scripts/dev.py` picks a free port automatically. When starting by
  hand, use another port (`runserver 8002`) and update `VITE_BACKEND_URL` to match.
- **The shop loads but shows no products / API errors:** the backend isn't running, or
  `VITE_BACKEND_URL` points at the wrong port. Restart `npm run dev` after changing `.env.local`.
- **Persian text errors in the Windows console:** run `set PYTHONUTF8=1` (cmd) or
  `$env:PYTHONUTF8=1` (PowerShell) first. `scripts/dev.py` does this for you.
- **Start over with a clean database:** stop the servers, delete `hooperzone/db.sqlite3` and
  `hooperzone/media/`, then run `python scripts/dev.py` again.

## Tests and checks

```bash
python -m pytest            # backend (run with the virtualenv active)
cd frontend && npm test     # frontend unit tests (vitest)
cd frontend && npm run lint # oxlint
```

## Production build

```bash
python scripts/package_wispbyte.py   # builds React and writes build/hooperzone-wispbyte.zip
```

Deployment to Wispbyte and hooperzone.ir is described step by step in
[DEPLOY_WISPBYTE.md](DEPLOY_WISPBYTE.md).

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
