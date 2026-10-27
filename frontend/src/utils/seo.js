import React, { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

// Keeps <head> in sync while the visitor navigates inside the app. The server
// (hooperzone/seo.py) renders the same tags into the first HTML response, which
// is what crawlers and link previews read.

const SITE_URL = import.meta.env.VITE_SITE_URL || window.location.origin;
const DEFAULT_IMAGE = `${import.meta.env.BASE_URL}og-default.jpg`;
const DEFAULT_DESCRIPTION = {
  fa: 'هوپرزون؛ فروشگاه تخصصی زانوبند، مچ‌بند، کمربند طبی و پوشاک فشاری ورزشی. ارسال به سراسر ایران با پست و تیپاکس و ۷ روز ضمانت بازگشت.',
  en: 'HooperZone: knee braces, wrist and ankle supports, back belts and compression wear. Nationwide delivery and 7-day returns.',
};

export const absoluteUrl = (url) => {
  if (!url) return '';
  if (/^https?:\/\//.test(url)) return url;
  return `${SITE_URL}${url.startsWith('/') ? '' : '/'}${url}`;
};

function upsert(selector, create, attrs) {
  let el = document.head.querySelector(selector);
  if (!el) {
    el = document.createElement(create);
    document.head.appendChild(el);
  }
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
}

const setName = (name, content) => upsert(`meta[name="${name}"]`, 'meta', { name, content });
const setProperty = (property, content) => upsert(`meta[property="${property}"]`, 'meta', { property, content });

/**
 * Page title, description, canonical URL and social tags.
 * `url` defaults to the current path (query strings are dropped so filter
 * variations share one canonical page). Pass `noindex` for private pages.
 */
export function usePageMeta(options = {}) {
  const { i18n } = useTranslation();
  const location = useLocation();
  const { title, description, keywords, image, url, type = 'website', noindex = false } = options;
  const lang = i18n.language === 'fa' ? 'fa' : 'en';

  useEffect(() => {
    const baseTitle = lang === 'fa' ? 'هوپرزون' : 'HooperZone';
    const pageTitle = title ? `${title} | ${baseTitle}` : baseTitle;
    const pageDescription = description || DEFAULT_DESCRIPTION[lang];
    const pageUrl = absoluteUrl(url || location.pathname);
    const pageImage = absoluteUrl(image || DEFAULT_IMAGE);

    document.title = pageTitle;
    setName('description', pageDescription);
    if (keywords) setName('keywords', keywords);
    setName('robots', noindex ? 'noindex, nofollow' : 'index, follow, max-image-preview:large');
    upsert('link[rel="canonical"]', 'link', { rel: 'canonical', href: pageUrl });

    setProperty('og:site_name', baseTitle);
    setProperty('og:locale', lang === 'fa' ? 'fa_IR' : 'en_US');
    setProperty('og:title', pageTitle);
    setProperty('og:description', pageDescription);
    setProperty('og:type', type);
    setProperty('og:url', pageUrl);
    setProperty('og:image', pageImage);

    setName('twitter:card', 'summary_large_image');
    setName('twitter:title', pageTitle);
    setName('twitter:description', pageDescription);
    setName('twitter:image', pageImage);
  }, [title, description, keywords, image, url, type, noindex, lang, location.pathname]);
}

function JsonLd({ data }) {
  // "</" can't appear inside a <script>, so escape it in case product text contains it.
  const json = JSON.stringify(data).replace(/<\//g, '<\\/');
  return React.createElement('script', { type: 'application/ld+json', dangerouslySetInnerHTML: { __html: json } });
}

export function ProductSchema({ product, url }) {
  if (!product) return null;
  const images = (product.images || []).map((img) => absoluteUrl(img.image));
  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.name_localized || product.name,
    description: product.description_localized || product.description,
    sku: product.slug,
    url: absoluteUrl(url || `/products/${product.slug}`),
    image: images,
    category: product.category?.name_localized || product.category?.name,
    offers: {
      '@type': 'Offer',
      url: absoluteUrl(url || `/products/${product.slug}`),
      // Prices are in Toman; schema.org needs an ISO currency, so send Rials.
      price: String(Math.round(Number(product.effective_price) * 10)),
      priceCurrency: 'IRR',
      itemCondition: 'https://schema.org/NewCondition',
      availability: product.in_stock ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock',
    },
  };
  if (product.brand) schema.brand = { '@type': 'Brand', name: product.brand };
  if (product.rating_count) {
    schema.aggregateRating = { '@type': 'AggregateRating', ratingValue: product.rating_average, reviewCount: product.rating_count };
  }
  return React.createElement(JsonLd, { data: schema });
}

// items: [{ label, to }] as passed to <Breadcrumbs>.
export function BreadcrumbSchema({ items }) {
  if (!items?.length) return null;
  const data = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: item.label,
      ...(item.to ? { item: absoluteUrl(item.to) } : {}),
    })),
  };
  return React.createElement(JsonLd, { data });
}
