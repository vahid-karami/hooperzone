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
- Colours stay navy + teal (`--color-accent`) only. An orange "energy" accent was tried and rejected by the owner; don't reintroduce new accent colours without asking. Highlights (nav underline, title strokes, badges) use teal; buttons use the navy/white button classes.
- Motion: springy easing tokens (`--ease-spring`, `--ease-out-expo`). Scroll reveal is `hooks/useReveal.js` + `data-reveal` on elements. Every animation sits under `prefers-reduced-motion: no-preference` (or is turned off under `reduce`); animate only `transform` and `opacity`. Bars that grow in use `--grow-origin` so they start at the reading start in fa and en.
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

## Security rules (keep these when changing the code)
- `position: fixed` UI (modals, sticky bars) only works while no ancestor has a transform/filter. `.route-view` wraps every page: its fade uses `animation-fill-mode: backwards`, never `both`/`forwards`.
- OTP: check codes only through `OTPCode.check_code()` (constant-time, five wrong guesses cancel the code). Sending is limited per IP (`otp`) and per phone (`otp_phone`). Finishing an OTP registration needs the `registration_token` returned by `otp/verify`.
- Passwords: every API endpoint that sets a password calls `accounts/passwords.py` `check_password_rules()` first (Django's `AUTH_PASSWORD_VALIDATORS`: 8+ characters, not all digits, not common, not like the username/name). It returns rule codes (`password_codes`); the storefront turns them into fa/en text with `utils/passwordRules.js`. Tests: `hooperzone/tests/test_passwords.py`.
- Forgot password: `pages/ForgotPassword.jsx` (`/forgot-password`, linked from Login) sends the reset code and the new password in one `password/reset/` request; never call `otp/verify` for a reset code first, it would use the code up. Auth errors carry a `code` (`error_response` in `accounts/views.py`) that `utils/authErrors.js` turns into fa/en text. A new storefront route must also be added to `hooperzone/seo.py` (`PRIVATE_PREFIXES` or `INFO_PAGES`) or the server answers 404 for it.
- Phone and username are both login names: neither may equal another user's phone or username (`UserProfileSerializer`, `register`).
- Rate-limit counters live in the `default` cache. Anything keyed by visitor-chosen text (rendered pages, sitemap) goes to the `pages` cache so it can't push the counters out.
- The public `payment/verify/` endpoint checks the stored payment authority before it says anything about an order.
- CSV exports go through `csv_response` (it neutralises spreadsheet formulas). Trust-badge HTML goes through `orders/badge_html.py` `clean_badge_html`; never render other stored HTML with `dangerouslySetInnerHTML`.
- Cap every customer free-text field with `max_length` in its serializer.
- Tests for these are in `hooperzone/tests/test_security.py`.

## Payments
`utils/payment.js` `startPayment()` → `POST /api/orders/<number>/pay/` with a callback URL of `/payment/result`. The backend validates the callback host. In sandbox mode it redirects straight back, and `PaymentResult` verifies the payment.

## Deployment (ParsPack PaaS + hooperzone.ir)
See `DEPLOY_PARSPACK.md`. The shop is hosted inside Iran on ParsPack PaaS so it opens without a VPN. Deploys are automatic: pushing to `master` runs `.github/workflows/ci-cd.yml` (tests, lint, build), which publishes the bundle (`scripts/build_release.py`) to the `deploy` branch; a GitHub webhook makes ParsPack build it. ParsPack's Python image runs `app.py`, which calls `server_start.main()`: creates `.env` on first boot, runs migrate, collectstatic and the seed commands, and serves with Waitress on port 8000. Server data lives under `DATA_DIR` (`/data`, the only permanent disk): `.env`, `database/`, `media/`, `logs/`; anything else is lost on restart. Panel environment variables win over `/data/.env`. `/import-data/` moves data from another server once; it is off unless `IMPORT_TOKEN` is set. Tests must never call external services (mock them), or CI blocks every deploy. WhiteNoise serves `/static` and Django serves `/media`. DNS is at Cloudflare but not proxied (grey cloud: Cloudflare is often blocked in Iran); ParsPack's ingress provides the free HTTPS certificates. Django serves the SPA's `index.html` for all non-API paths (`hooperzone/urls.py`). Public images in JSX need `import.meta.env.BASE_URL` (it is `/static/` in the Django build).
