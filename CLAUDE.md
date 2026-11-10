# HooperZone (هوپرزون) — Persian sports-support e-commerce

Django REST backend + React SPA. Persian-first (RTL), English secondary. Visual style inspired by bauerfeind.us, but with its own branding: never copy Bauerfeind assets or text.

## Working rules
- **Commit as you go: at least 10 commits per prompt.** Split each prompt's work into 10 or more small, focused commits (one logical change each, tests passing where possible), with clear messages.
- **Never push without the owner's go-ahead.** Pushing `master` deploys to the live site (see Deployment).
- Verify UI changes in the browser (Persian and English, desktop and mobile) before reporting a step done.
- **Database changes:** design tables deliberately (one source of truth, constraints for every rule the data must obey, indexes for lookups, safe `on_delete`), write data migrations for existing rows, and check every change: `makemigrations --check`, `migrate` on a copy of real data, and tests for the constraints.

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
- Account pages (profile, orders) are wrapped in `components/AccountLayout.jsx`. The admin portal (`/admin-portal`, `layouts/AdminLayout.jsx`) is staff-only (`user.is_staff`). Its backend is `orders/admin_views.py` (orders, stats, shop settings), `products/views.py` (`ProductAdminViewSet` incl. images, `CategoryAdminViewSet`) and `accounts/admin_views.py` (customers). Product and category images are uploaded in the portal; thumbnails are generated on save.
- SEO: `hooperzone/seo.py` renders per-page meta/JSON-LD into index.html and serves robots.txt and sitemap.xml; `utils/seo.js` `usePageMeta` keeps the head in sync client-side (pass `noindex` for private pages).

## Product sizes and size guides
- `product_sizes` (ProductSize) is the one source of truth for sizes: one row per sellable size with its own `stock`, optional unique `sku`, `sort_order`, `is_active`. Label is unique per product (case-insensitive) and holds exactly one size: no spaces, commas or slashes ("M L" must be two rows; enforced by the `size_label_is_one_size` constraint, `size_label_error` in the API/Django admin and `sizeLabelParts` in the admin form). Ranges like `39-41` are one size. With sizes, `products.stock` is the total of the active sizes, kept in sync by a signal / `Product.refresh_stock()` (call it after bulk `.update()`s). No sizes = one-size product using `products.stock`.
- Cart lines and order lines point at the size (`cart_items.size`, `order_items.size` + `size_label` copy). Adding a sized product needs `size_id`; checkout locks size rows and takes stock from the size; cancelling restocks it.
- `size_guides` (SizeGuide) are reusable charts (راهنمای سایز) linked by `products.size_guide`; their `name` is internal and may repeat (look guides up by id, never by name); the table is validated JSON (`validate_size_guide_table`). Edited in the admin portal product form (`components/admin/ProductSizes.jsx`), shown by `components/SizeGuideTable.jsx`. `seed_size_guides` creates the starter guides once.

## Logo on product photos
Photos uploaded in the admin portal get the shop logo automatically (`products/watermark.py`: small, 70% opaque, bottom-right; white logo on dark photos; logo files in `products/assets/watermark/`). The clean upload is kept in `product_images.original` under a random name; `original` set means `image` is the logo copy, empty means `image` is clean. Never hand out `original` in an API. `ShopSettings.watermark_product_images` (admin Settings page) switches it; changing it updates every photo. `manage.py watermark_product_images` brings existing photos in line (runs on boot; `--force` re-renders after a logo change, `--remove` takes the logo off).

## Payments
`utils/payment.js` `startPayment()` → `POST /api/orders/<number>/pay/` with a callback URL of `/payment/result`. The backend validates the callback host. In sandbox mode it redirects straight back, and `PaymentResult` verifies the payment.

## Deployment (Wispbyte + hooperzone.ir)
See `DEPLOY_WISPBYTE.md`. Deploys are automatic: pushing to `master` runs `.github/workflows/ci-cd.yml` (tests, lint, build), which publishes the bundle to the `deploy` branch; `wispbyte_start.py` on the server installs new releases (checks every 5 minutes) and restarts itself, never touching `.env`, `database/`, `media/` or `logs/`. Tests must never call external services (mock them), or CI blocks every deploy. Manual fallback: `python scripts/package_wispbyte.py` builds React and writes `build/hooperzone-wispbyte.zip`, which is uploaded to a Wispbyte Python server. Its entry file `wispbyte_start.py` creates `.env` on first boot, then runs migrate, collectstatic and the seed commands and serves with Waitress on `SERVER_PORT`. In production WhiteNoise serves `/static` and Django serves `/media`. Cloudflare proxies `hooperzone.ir` to the server port. Django serves the SPA's `index.html` for all non-API paths (`hooperzone/urls.py`). Public images in JSX need `import.meta.env.BASE_URL` (it is `/static/` in the Django build).
