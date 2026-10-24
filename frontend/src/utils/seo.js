import React, { useEffect } from 'react';
import { useTranslation } from 'react-i18next';

export function usePageMeta(options = {}) {
  const { i18n } = useTranslation();
  const {
    title,
    description,
    keywords,
    image,
    url,
    type = 'website',
  } = options;

  useEffect(() => {
    const baseTitle = i18n.language === 'fa' ? 'هوپرزون' : 'HooperZone';
    const pageTitle = title ? `${title} | ${baseTitle}` : baseTitle;
    const pageDescription = description || 'Sports recovery and support products designed to help you stay active, recover confidently, and perform at your best.';

    document.title = pageTitle;

    const setMeta = (name, content) => {
      let meta = document.querySelector(`meta[name="${name}"]`);
      if (!meta) {
        meta = document.createElement('meta');
        meta.setAttribute('name', name);
        document.head.appendChild(meta);
      }
      meta.setAttribute('content', content);
    };

    const setProperty = (property, content) => {
      let meta = document.querySelector(`meta[property="${property}"]`);
      if (!meta) {
        meta = document.createElement('meta');
        meta.setAttribute('property', property);
        document.head.appendChild(meta);
      }
      meta.setAttribute('content', content);
    };

    setMeta('description', pageDescription);
    if (keywords) setMeta('keywords', keywords);

    setProperty('og:title', pageTitle);
    setProperty('og:description', pageDescription);
    setProperty('og:type', type);
    if (image) setProperty('og:image', image);
    if (url) setProperty('og:url', url);

    setProperty('twitter:card', 'summary_large_image');
    setProperty('twitter:title', pageTitle);
    setProperty('twitter:description', pageDescription);
    if (image) setProperty('twitter:image', image);
  }, [title, description, keywords, image, url, type, i18n.language]);
}

export function ProductSchema({ product }) {
  if (!product) return null;

  const schema = {
    '@context': 'https://schema.org',
    '@type': 'Product',
    name: product.name_localized || product.name,
    description: product.description_localized || product.description,
    image: product.images?.[0]?.image || '',
    offers: {
      '@type': 'Offer',
      price: product.effective_price,
      priceCurrency: 'IRT',
      availability: product.in_stock
        ? 'https://schema.org/InStock'
        : 'https://schema.org/OutOfStock',
    },
  };

  return React.createElement('script', {
    type: 'application/ld+json',
    dangerouslySetInnerHTML: { __html: JSON.stringify(schema) },
  });
}
