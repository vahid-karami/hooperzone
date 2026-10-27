"""Search-engine support for the React app.

The SPA renders in the browser, so crawlers and link previews (Telegram, WhatsApp,
Google) would otherwise see the same generic <head> on every URL. `render_page`
fills in each page's title, description, canonical URL, Open Graph tags and
JSON-LD before index.html is sent, and reports unknown URLs as 404.
"""
import html
import json
import re
from dataclasses import dataclass, field

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.core.cache import cache
from django.db.models import Avg, Count
from django.http import HttpResponse
from django.urls import reverse
from django.utils.html import strip_tags

SITE_NAME = "هوپرزون"
SITE_NAME_EN = "HooperZone"
DEFAULT_TITLE = "هوپرزون | ساپورت‌ها و بریس‌های ورزشی و طبی"
DEFAULT_DESCRIPTION = (
    "هوپرزون؛ فروشگاه تخصصی زانوبند، مچ‌بند، کمربند طبی و پوشاک فشاری ورزشی. "
    "ارسال به سراسر ایران با پست و تیپاکس و ۷ روز ضمانت بازگشت."
)
CACHE_SECONDS = 300

# Pages that exist in the React app but shouldn't be indexed (personal or transactional).
PRIVATE_PREFIXES = (
    "/cart", "/checkout", "/login", "/register", "/profile", "/orders", "/payment",
    "/favorites", "/admin-portal",
)

INFO_PAGES = {
    "/about": ("درباره هوپرزون", "آشنایی با هوپرزون، فروشگاه تخصصی ساپورت‌ها و بریس‌های ورزشی و طبی."),
    "/contact": ("تماس با ما", "راه‌های تماس با پشتیبانی هوپرزون برای مشاوره خرید و پیگیری سفارش."),
    "/faq": ("پرسش‌های متداول", "پاسخ پرسش‌های رایج درباره خرید، ارسال، انتخاب سایز و بازگشت کالا."),
    "/shipping": ("شیوه‌های ارسال", "ارسال سفارش با پست سفارشی، پست پیشتاز و تیپاکس به سراسر ایران."),
    "/returns": ("شرایط بازگشت کالا", "۷ روز ضمانت بازگشت کالا در هوپرزون و مراحل ثبت درخواست مرجوعی."),
    "/terms": ("قوانین و مقررات", "قوانین خرید از فروشگاه اینترنتی هوپرزون."),
    "/privacy": ("حریم خصوصی", "نحوه نگهداری و استفاده از اطلاعات کاربران در هوپرزون."),
    "/categories": ("دسته‌بندی محصولات", "همه دسته‌بندی‌های ساپورت، بریس و پوشاک فشاری ورزشی و طبی."),
}


@dataclass
class PageMeta:
    title: str = DEFAULT_TITLE
    description: str = DEFAULT_DESCRIPTION
    path: str = "/"
    image: str = ""
    og_type: str = "website"
    noindex: bool = False
    status: int = 200
    json_ld: list = field(default_factory=list)


def absolute(url):
    if not url:
        return ""
    if url.startswith("http"):
        return url
    return f"{settings.SITE_URL}/{url.lstrip('/')}"


def clean_text(text, limit=160):
    text = re.sub(r"\s+", " ", strip_tags(text or "")).strip()
    return text if len(text) <= limit else text[: limit - 1].rsplit(" ", 1)[0] + "…"


def breadcrumbs(*items):
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": name, "item": absolute(path)}
            for i, (name, path) in enumerate(items, start=1)
        ],
    }


def organization_ld():
    from orders.models import ShopSettings

    shop = ShopSettings.load()
    org = {
        "@context": "https://schema.org",
        "@type": "OnlineStore",
        "name": SITE_NAME,
        "alternateName": SITE_NAME_EN,
        "url": settings.SITE_URL,
        "logo": absolute(f"{settings.STATIC_URL}favicon.svg"),
    }
    if shop.store_phone:
        org["telephone"] = shop.store_phone
    if shop.store_email:
        org["email"] = shop.store_email
    if shop.store_address:
        org["address"] = {"@type": "PostalAddress", "streetAddress": shop.store_address, "addressCountry": "IR"}
    same_as = [
        f"https://instagram.com/{shop.instagram}" if shop.instagram else "",
        f"https://t.me/{shop.telegram}" if shop.telegram else "",
    ]
    if any(same_as):
        org["sameAs"] = [s for s in same_as if s]
    website = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "url": settings.SITE_URL,
        "inLanguage": "fa-IR",
        "potentialAction": {
            "@type": "SearchAction",
            "target": f"{settings.SITE_URL}/products?search={{search_term_string}}",
            "query-input": "required name=search_term_string",
        },
    }
    return [org, website]


def product_meta(slug):
    from products.models import Product

    product = (
        Product.objects.filter(slug=slug, is_active=True)
        .select_related("category")
        .prefetch_related("images")
        .annotate(rating_avg=Avg("reviews__rating"), rating_count=Count("reviews"))
        .first()
    )
    if not product:
        return None
    name = product.name_fa or product.name
    images = sorted(product.images.all(), key=lambda i: (not i.is_primary, -i.created_at.timestamp()))
    image_urls = [absolute(i.image.url) for i in images]
    description = clean_text(product.meta_description or product.description_fa or product.description)
    category_name = product.category.name_fa or product.category.name
    url = f"/products/{product.slug}"

    offer = {
        "@type": "Offer",
        "url": absolute(url),
        # Prices are stored in Toman, which isn't an ISO currency; Google expects Rials.
        "price": str(int(product.effective_price) * 10),
        "priceCurrency": "IRR",
        "availability": "https://schema.org/InStock" if product.in_stock else "https://schema.org/OutOfStock",
        "itemCondition": "https://schema.org/NewCondition",
    }
    ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": name,
        "description": description,
        "sku": product.slug,
        "url": absolute(url),
        "image": image_urls,
        "category": category_name,
        "offers": offer,
    }
    if product.brand:
        ld["brand"] = {"@type": "Brand", "name": product.brand}
    if product.rating_count:
        ld["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": round(product.rating_avg, 1),
            "reviewCount": product.rating_count,
        }
    return PageMeta(
        title=f"{product.meta_title or name} | {SITE_NAME}",
        description=description or DEFAULT_DESCRIPTION,
        path=url,
        image=image_urls[0] if image_urls else "",
        og_type="product",
        json_ld=[
            ld,
            breadcrumbs(
                ("خانه", "/"), ("فروشگاه", "/products"),
                (category_name, f"/products?category={product.category.slug}"), (name, url),
            ),
        ],
    )


def products_meta(request):
    from products.models import Category, Sport

    category = request.GET.get("category")
    sport = request.GET.get("sport")
    if category:
        cat = Category.objects.filter(slug=category, is_active=True).first()
        if not cat:
            return PageMeta(title=f"صفحه پیدا نشد | {SITE_NAME}", noindex=True, status=404, path="/products")
        name = cat.name_fa or cat.name
        return PageMeta(
            title=f"{cat.meta_title or 'خرید ' + name} | {SITE_NAME}",
            description=clean_text(cat.meta_description or cat.description_fa or cat.description) or DEFAULT_DESCRIPTION,
            path=f"/products?category={cat.slug}",
            image=absolute(cat.image.url) if cat.image else "",
            json_ld=[breadcrumbs(("خانه", "/"), ("فروشگاه", "/products"), (name, f"/products?category={cat.slug}"))],
        )
    if sport:
        sp = Sport.objects.filter(slug=sport, is_active=True).first()
        if sp:
            name = sp.name_fa or sp.name
            return PageMeta(
                title=f"ساپورت‌های مناسب {name} | {SITE_NAME}",
                description=f"زانوبند، مچ‌بند و ساپورت‌های پیشنهادی برای {name}؛ ارسال به سراسر ایران.",
                path=f"/products?sport={sp.slug}",
            )
    # Other filters (search, price, sort) are variations of the main listing.
    return PageMeta(
        title=f"فروشگاه ساپورت و بریس ورزشی | {SITE_NAME}",
        description="خرید آنلاین زانوبند، مچ‌بند، قوزک‌بند، کمربند طبی و پوشاک فشاری با ضمانت اصالت و ارسال سریع.",
        path="/products",
        json_ld=[breadcrumbs(("خانه", "/"), ("فروشگاه", "/products"))],
    )


def page_meta(request):
    path = request.path.rstrip("/") or "/"
    if path == "/":
        return PageMeta(path="/", json_ld=organization_ld())
    if path == "/products":
        return products_meta(request)
    match = re.fullmatch(r"/products/([\w-]+)", path)
    if match:
        meta = product_meta(match.group(1))
        return meta or PageMeta(title=f"محصول پیدا نشد | {SITE_NAME}", noindex=True, status=404, path=path)
    if path in INFO_PAGES:
        title, description = INFO_PAGES[path]
        return PageMeta(title=f"{title} | {SITE_NAME}", description=description, path=path)
    if path.startswith(PRIVATE_PREFIXES):
        return PageMeta(noindex=True, path=path)
    return PageMeta(title=f"صفحه پیدا نشد | {SITE_NAME}", noindex=True, status=404, path=path)


def head_tags(meta):
    esc = lambda v: html.escape(v, quote=True)  # noqa: E731
    url = absolute(meta.path)
    image = meta.image or absolute(f"{settings.STATIC_URL}og-default.jpg")
    tags = [
        f'<link rel="canonical" href="{esc(url)}" />',
        f'<meta property="og:site_name" content="{SITE_NAME}" />',
        '<meta property="og:locale" content="fa_IR" />',
        f'<meta property="og:type" content="{esc(meta.og_type)}" />',
        f'<meta property="og:title" content="{esc(meta.title)}" />',
        f'<meta property="og:description" content="{esc(meta.description)}" />',
        f'<meta property="og:url" content="{esc(url)}" />',
        f'<meta property="og:image" content="{esc(image)}" />',
        '<meta name="twitter:card" content="summary_large_image" />',
        f'<meta name="twitter:title" content="{esc(meta.title)}" />',
        f'<meta name="twitter:description" content="{esc(meta.description)}" />',
        f'<meta name="twitter:image" content="{esc(image)}" />',
    ]
    for block in meta.json_ld:
        # "</" can't appear inside a <script>; escape it for JSON that contains user text.
        data = json.dumps(block, ensure_ascii=False).replace("</", "<\\/")
        tags.append(f'<script type="application/ld+json">{data}</script>')
    return "\n    ".join(tags)


def inject(index_html, meta):
    esc = lambda v: html.escape(v, quote=True)  # noqa: E731
    out = re.sub(r"<title>.*?</title>", f"<title>{esc(meta.title)}</title>", index_html, count=1, flags=re.S)
    out = re.sub(
        r'<meta name="description" content="[^"]*"\s*/?>',
        f'<meta name="description" content="{esc(meta.description)}" />',
        out, count=1,
    )
    robots = "noindex, nofollow" if meta.noindex else "index, follow, max-image-preview:large"
    out = re.sub(r'<meta name="robots" content="[^"]*"\s*/?>', f'<meta name="robots" content="{robots}" />', out, count=1)
    return out.replace("</head>", f"    {head_tags(meta)}\n  </head>", 1)


def render_page(request, index_html):
    """index.html with this URL's meta tags, and its HTTP status (404 for unknown pages)."""
    key = f"seo:{request.get_full_path()}"
    cached = cache.get(key)
    if cached is None:
        meta = page_meta(request)
        cached = (inject(index_html, meta), meta.status)
        cache.set(key, cached, CACHE_SECONDS)
    body, status = cached
    response = HttpResponse(body, status=status)
    response["Cache-Control"] = "no-cache"
    return response


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /admin-portal",
        "Disallow: /api/",
        "Disallow: /cart",
        "Disallow: /checkout",
        "Disallow: /profile",
        "Disallow: /orders",
        "Disallow: /payment/",
        "Disallow: /favorites",
        "Disallow: /login",
        "Disallow: /register",
        "Disallow: /products?*search=",
        "Allow: /",
        "",
        f"Sitemap: {settings.SITE_URL}{reverse('sitemap')}",
        "",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


class SiteSitemap(Sitemap):
    protocol = "https"

    def get_domain(self, site=None):
        return settings.SITE_URL.split("://", 1)[-1]


class StaticSitemap(SiteSitemap):
    changefreq = "monthly"

    def items(self):
        return ["/", "/products", "/categories", *INFO_PAGES.keys()]

    def location(self, item):
        return item

    def priority(self, item):
        return 1.0 if item == "/" else 0.8 if item in ("/products", "/categories") else 0.3


class ProductSitemap(SiteSitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        from products.models import Product

        return Product.objects.filter(is_active=True).prefetch_related("images").order_by("-updated_at")

    def location(self, product):
        return f"/products/{product.slug}"

    def lastmod(self, product):
        return product.updated_at

    def get_urls(self, *args, **kwargs):
        # Adds <image:image> entries (see templates/sitemap.xml) so product photos get indexed.
        urls = super().get_urls(*args, **kwargs)
        for url in urls:
            url["images"] = [absolute(i.image.url) for i in url["item"].images.all()]
        return urls


class CategorySitemap(SiteSitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        from products.models import Category

        return Category.objects.filter(is_active=True).order_by("name")

    def location(self, category):
        return f"/products?category={category.slug}"


class SportSitemap(SiteSitemap):
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        from products.models import Sport

        return Sport.objects.filter(is_active=True)

    def location(self, sport):
        return f"/products?sport={sport.slug}"


SITEMAPS = {
    "pages": StaticSitemap,
    "products": ProductSitemap,
    "categories": CategorySitemap,
    "sports": SportSitemap,
}
