# HooperZone - Development TODO

## Phase 1: Internationalization (i18n) Setup
- [x] Install and configure react-i18next for React
- [x] Create English translation files (en.json)
- [x] Create Persian translation files (fa.json)
- [x] Add language switcher component to header
- [x] Implement RTL (Right-to-Left) layout support for Persian
- [x] Create useLanguage hook for language management
- [x] Store language preference in localStorage

## Phase 2: Persian Frontend Development
- [x] Research Persian e-commerce UI patterns (Digikala, Torob, etc.)
- [x] Create Persian CSS with RTL support
- [x] Translate all pages to Persian:
  - [x] Homepage
  - [x] Products page
  - [x] Product detail page
  - [x] Cart page
  - [x] Checkout page
  - [x] Login/Register pages
  - [x] Profile page
  - [x] Orders page
  - [x] Favorites page
- [x] Add Persian fonts (Vazir, IRANSans, or Samim)
- [x] Implement number formatting for Persian digits (۱۲۳۴)
- [x] Add Persian date formatting

## Phase 3: Backend Persian Support
- [x] Add Persian fields to models:
  - [x] Product: name_fa, description_fa, price_irr, cost, cost_irr
  - [x] Category: name_fa, description_fa
- [x] Update serializers to include Persian fields
- [x] Add language parameter to API endpoints (?lang=fa)
- [x] Create Persian seed data

## Product Management Portal
- [x] Create admin product API endpoint (ProductAdminViewSet)
- [x] Create admin product management frontend page
- [x] Add cost tracking and margin calculation

## Phase 4: Currency & Pricing
- [x] Standardize exclusively on Toman (تومان) currency across entire project
- [x] Remove Dollar (USD) and Rial (IRR) from frontend and selector
- [x] Add Persian number formatting with comma separators for Toman prices
- [x] Update all price display components (<Price />)

## Phase 5: Iranian Market Features
- [x] Add Iranian phone number validation (+98 format)
- [x] Direct username and password registration & login without mandatory OTP
- [x] Multi-identifier authentication (username, phone, or email)
- [x] Create Iranian address structure (Province, City, Postal code)
- [x] Add Iranian provinces and cities data
- [x] Prepare for Iranian payment gateways (Zarinpal, Idpay)
- [x] Add Persian calendar support

## Phase 6: UI/UX Improvements
- [x] Add loading skeletons for all pages
- [x] Improve mobile responsiveness
- [x] Add toast notifications
- [x] Implement smooth page transitions
- [x] Add product quick view modal
- [x] Improve accessibility (ARIA labels, keyboard navigation)

## Phase 7: Performance & SEO
- [x] Implement React.lazy for code splitting
- [x] Add meta tags for SEO
- [x] Implement Open Graph tags for social sharing
- [x] Add structured data (JSON-LD) for products
- [x] Optimize images with lazy loading
- [x] Add service worker for PWA support

## Phase 8: Testing & Quality
- [x] Add Persian language tests
- [x] Test RTL layout thoroughly
- [x] Add unit tests for components
- [x] Perform cross-browser testing (CSS fallbacks added)
- [x] Test mobile responsiveness

---

## Persian E-commerce Research Notes

### Popular Iranian Online Shops
1. **Digikala** (دیجیکالا) - Largest Iranian e-commerce
   - Clean, minimal design
   - Blue and white color scheme
   - Grid-based product listings
   - Advanced filtering system
   - Product comparison feature

2. **Torob** (ترب) - Price comparison
   - Simple, fast interface
   - Focus on price comparison
   - Clean product cards

3. **Bamilo** (بامیلو) - Fashion & lifestyle
   - Modern design
   - Large hero banners
   - Category-based navigation

4. **Modiseh** (مدیسه) - Fashion
   - Elegant design
   - High-quality product images
   - Persian typography focus

### Persian UI Patterns
- **RTL Layout**: Right-to-left text and layout
- **Persian Fonts**: Vazir, IRANSans, Samim, Shabnam
- **Number System**: Persian digits (۰۱۲۳۴۵۶۷۸۹)
- **Currency**: Toman (تومان) - 1 Toman = 10 Rials
- **Dates**: Persian (Jalali) calendar
- **Phone Numbers**: +98 format
- **Colors**: Blue (trust), Green (success), Red (sale)

### Persian Typography Best Practices
- Use web-safe Persian fonts
- Line height: 1.8-2.0 for readability
- Font size: 14px minimum for body text
- Proper letter spacing for Persian script

---

## Language File Structure

```
frontend/src/
├── i18n/
│   ├── index.js          # i18n configuration
│   ├── locales/
│   │   ├── en.json       # English translations
│   │   └── fa.json       # Persian translations
│   └── hooks/
│       └── useLanguage.js
├── components/
│   └── LanguageSwitcher.jsx
└── styles/
    ├── design-tokens.css
    ├── main.css
    └── rtl.css           # RTL specific styles
```

---

## Key Persian Translations

| English | Persian |
|---------|---------|
| Shop | فروشگاه |
| Products | محصولات |
| Cart | سبد خرید |
| Checkout | تکمیل خرید |
| Login | ورود |
| Register | ثبت‌نام |
| Profile | پروفایل |
| Orders | سفارش‌ها |
| Favorites | علاقه‌مندی‌ها |
| Search | جستجو |
| Price | قیمت |
| Free Shipping | ارسال رایگان |
| In Stock | موجود در انبار |
| Add to Cart | افزودن به سبد خرید |
| Knee | زانو |
| Ankle | مچ پا |
| Back | کمر |
| Shoulder | شانه |
| Wrist | مچ دست |
| Elbow | آرنج |

---

## Implementation Priority

1. **High Priority**: i18n setup, RTL support, Persian translations
2. **Medium Priority**: Persian fonts, number formatting, currency
3. **Low Priority**: Payment gateway, Persian calendar, PWA
