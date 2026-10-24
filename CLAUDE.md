# HooperZone (هوپرزون) — Persian sports-support e-commerce

Django REST backend + React SPA. Persian-first (RTL), English secondary. Visual style inspired by bauerfeind.us, but with its own branding: never copy Bauerfeind assets or text.

## Working rules
- **Never commit or push.** After each finished step, report the changed files and a suggested commit message. The owner commits.
- Verify UI changes in the browser (Persian and English, desktop and mobile) before reporting a step done.

## Stack
- Backend: Django 6, DRF, simplejwt. Apps: `accounts` (phone-number users), `products` (products, categories, sports, images), `cart`, `orders` (orders, payments, staff admin API), `favorites`, `reviews`.
- Settings: `hooperzone/settings/{base,local,production}.py`. The default is `local` (SQLite `hooperzone/db.sqlite3`).
- Frontend: `frontend/` with React 19, Vite 8, react-i18next, vitest, oxlint.

## Commands (run from repo root on Windows)
One command from any fresh clone: `python scripts/dev.py` (sets up venv, npm packages, migrations and demo data on first run, then starts backend and frontend; `backend` or `frontend` as an argument starts just one). Claude preview configs are in `.claude/launch.json` and VS Code debug configs in `.vscode/launch.json`.
```
venv\Scripts\python manage.py runserver 8001      # port 8000 is taken on this PC
venv\Scripts\python -m pytest                     # backend tests
venv\Scripts\python manage.py seed_demo_store     # demo catalog; also seed_sports, seed_category_images, seed_product_images
cd frontend && npm run dev                        # http://localhost:5173
cd frontend && npm test                           # vitest
cd frontend && npm run lint
cd frontend && npm run build:django               # production build served by Django under /static/
```
`frontend/.env.local` sets `VITE_BACKEND_URL=http://localhost:8001`. The Vite dev server proxies `/api` and `/media` to that URL.

## Frontend conventions
- RTL first: use logical CSS properties (`margin-inline-start`, `inset-inline-end`) and never mirror icons with `scaleX(-1)`.
- Design tokens are in `styles/design-tokens.css`: navy `#12348f` primary, sky `#e8eef7` surfaces, Vazirmatn font, pill buttons.
- Stylesheets by area: `storefront.css` (header/home), `catalog.css`, `pages.css`, `product.css`, `checkout.css`, `account.css` (profile/orders/admin), `rtl.css`. `main.css` is legacy; don't add to it, and prune dead rules when you replace markup.
- Every UI string uses `t('key', 'Persian default')`, and the key must exist in both `i18n/locales/fa.json` and `en.json`.
- Persian digits: normalize input with `utils/digits.js` `toEnglishDigits`; display numbers with `toPersianNumber` (`hooks/useLanguage.js`). The backend also accepts Persian digits (`hooperzone/fields.py` `DigitsCharField`).
- API paths live in `api/endpoints.js`. For paginated lists that need every page, use `utils/fetchAll.js` `fetchAllPages`.
- Account pages (profile, orders) are wrapped in `components/AccountLayout.jsx`. The admin portal (`/admin-portal`, `layouts/AdminLayout.jsx`) is staff-only (`user.is_staff`) and has its backend in `orders/admin_views.py`. Images for products and categories are uploaded in Django admin (`/admin/`).

## Payments
`utils/payment.js` `startPayment()` → `POST /api/orders/<number>/pay/` with a callback URL of `/payment/result`. The backend validates the callback host. In sandbox mode it redirects straight back, and `PaymentResult` verifies the payment.

## Deployment (Wispbyte + hooperzone.ir)
See `DEPLOY_WISPBYTE.md`. `python scripts/package_wispbyte.py` builds React and writes `build/hooperzone-wispbyte.zip`, which is uploaded to a Wispbyte Python server. Its entry file `wispbyte_start.py` creates `.env` on first boot, then runs migrate, collectstatic and the seed commands and serves with Waitress on `SERVER_PORT`. In production WhiteNoise serves `/static` and Django serves `/media`. Cloudflare proxies `hooperzone.ir` to the server port. Django serves the SPA's `index.html` for all non-API paths (`hooperzone/urls.py`). Public images in JSX need `import.meta.env.BASE_URL` (it is `/static/` in the Django build).
