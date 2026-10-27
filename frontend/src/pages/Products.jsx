import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import ProductCard from '../components/ProductCard';
import { ProductCardSkeleton } from '../components/Skeletons';
import Icon from '../components/Icon';
import Breadcrumbs from '../components/Breadcrumbs';
import { BODY_PARTS, bodyPartLabel } from '../utils/bodyParts';
import { toPersianNumber } from '../hooks/useLanguage';
import { usePageMeta } from '../utils/seo';
import { useCategories, useSports, sportName } from '../utils/catalog';

const PAGE_SIZE = 20;

function FilterPill({ label, count = 0, children }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => {
      if (!ref.current?.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div className={`filter-pill ${open ? 'open' : ''} ${count ? 'has-value' : ''}`} ref={ref}>
      <button type="button" className="filter-pill-btn" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        {label}
        {count > 0 && <span className="filter-pill-count">{count}</span>}
        <Icon name={open ? 'minus' : 'plus'} size={16} />
      </button>
      {open && <div className="filter-popover">{children({ close: () => setOpen(false) })}</div>}
    </div>
  );
}

export default function Products() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const [searchParams, setSearchParams] = useSearchParams();
  const [products, setProducts] = useState([]);
  const categories = useCategories();
  const sports = useSports();
  const [loading, setLoading] = useState(true);
  const [totalCount, setTotalCount] = useState(0);

  const category = searchParams.get('category') || '';
  const injuryType = searchParams.get('injury_type') || '';
  const sport = searchParams.get('sport') || '';
  const search = searchParams.get('search') || '';
  const inStock = searchParams.get('in_stock') || '';
  const onSale = searchParams.get('on_sale') || '';
  const minPrice = searchParams.get('min_price') || '';
  const maxPrice = searchParams.get('max_price') || '';
  const ordering = searchParams.get('ordering') || '';
  const page = Math.max(1, Number(searchParams.get('page')) || 1);

  const [priceDraft, setPriceDraft] = useState({ min: minPrice, max: maxPrice });

  const currentCategory = categories.find((c) => c.slug === category);
  const categoryName = currentCategory ? (lang === 'fa' && currentCategory.name_fa) || currentCategory.name : '';
  const currentSport = sports.find((s) => s.slug === sport);
  const currentSportName = currentSport ? sportName(currentSport, lang) : sport;

  let title = t('products.allProducts');
  let subtitle = t('products.allProductsDesc', 'ساپورت‌ها، بریس‌ها و پوشاک فشاری برای پیشگیری، درمان و عملکرد بهتر.');
  if (search) {
    title = t('products.searchResults', 'نتایج جستجو برای «{{query}}»', { query: search });
    subtitle = '';
  } else if (currentCategory) {
    title = categoryName;
    subtitle = (lang === 'fa' && currentCategory.description_fa) || currentCategory.description || subtitle;
  } else if (sport) {
    title = t('products.sportTitle', 'ساپورت‌های مناسب {{sport}}', { sport: currentSportName });
    subtitle = t('products.sportDesc', 'محصولاتی که برای این ورزش پیشنهاد می‌کنیم.');
  } else if (injuryType) {
    const part = BODY_PARTS.find((p) => p.key === injuryType);
    title = t('products.bodyPartTitle', 'ساپورت‌های {{part}}', { part: bodyPartLabel(injuryType, lang) });
    subtitle = part ? (lang === 'fa' ? part.blurbFa : part.blurbEn) : subtitle;
  } else if (onSale) {
    title = t('header.offers', 'تخفیف‌ها');
    subtitle = t('products.offersDesc', 'منتخبی از ساپورت‌ها با قیمت ویژه.');
  }

  // Category and sport listings are their own pages; other filters share the main listing's canonical URL.
  const canonical = category ? `/products?category=${category}` : sport ? `/products?sport=${sport}` : '/products';
  usePageMeta({ title, description: subtitle || title, url: canonical });

  useEffect(() => {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (injuryType) params.append('injury_type', injuryType);
    if (sport) params.append('sport', sport);
    if (search) params.append('search', search);
    if (inStock) params.append('in_stock', inStock);
    if (onSale) params.append('on_sale', onSale);
    if (minPrice) params.append('min_price', minPrice);
    if (maxPrice) params.append('max_price', maxPrice);
    if (ordering) params.append('ordering', ordering);
    params.append('page', page);

    let cancelled = false;
    setLoading(true);
    apiClient
      .get(`${ENDPOINTS.products}?${params}`)
      .then((response) => {
        if (cancelled) return;
        setProducts(response.data.results);
        setTotalCount(response.data.count);
      })
      .catch((error) => {
        if (cancelled) return;
        console.error('Failed to fetch products:', error);
        setProducts([]);
        setTotalCount(0);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [category, injuryType, sport, search, inStock, onSale, minPrice, maxPrice, ordering, page]);

  const updateParams = (changes) => {
    const next = new URLSearchParams(searchParams);
    Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)));
    if (!('page' in changes)) next.delete('page');
    setSearchParams(next);
  };

  const clearFilters = () => {
    setPriceDraft({ min: '', max: '' });
    setSearchParams(search ? { search } : {});
  };

  const goToPage = (p) => {
    updateParams({ page: p > 1 ? String(p) : '' });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

  const activeChips = [];
  if (injuryType) activeChips.push({ key: 'injury_type', label: bodyPartLabel(injuryType, lang) });
  if (sport) activeChips.push({ key: 'sport', label: currentSportName });
  if (category) activeChips.push({ key: 'category', label: categoryName || category });
  if (onSale) activeChips.push({ key: 'on_sale', label: t('header.offers', 'تخفیف‌ها') });
  if (inStock) activeChips.push({ key: 'in_stock', label: t('products.inStockOnly') });
  if (minPrice || maxPrice) {
    activeChips.push({
      key: 'price',
      label: `${minPrice ? num(Number(minPrice).toLocaleString('en-US')) : '۰'} – ${maxPrice ? num(Number(maxPrice).toLocaleString('en-US')) : '∞'}`,
    });
  }

  const removeChip = (key) => {
    if (key === 'price') {
      setPriceDraft({ min: '', max: '' });
      updateParams({ min_price: '', max_price: '' });
    } else {
      updateParams({ [key]: '' });
    }
  };

  const sortOptions = [
    { value: '', label: t('products.featured') },
    { value: '-created_at', label: t('products.newest') },
    { value: 'price', label: t('products.priceLowHigh') },
    { value: '-price', label: t('products.priceHighLow') },
  ];

  const bannerImage = products.find((p) => p.primary_image)?.primary_image?.image;

  const crumbs = [
    { to: '/', label: t('common.home') },
    { to: '/products', label: t('common.shop') },
  ];
  if (title !== t('products.allProducts')) crumbs.push({ label: title });

  return (
    <div className="listing-page">
      <div className="container">
        <Breadcrumbs items={crumbs} />

        <header className="listing-banner">
          <div className="listing-banner-copy">
            <h1>{title}</h1>
            {subtitle && <p>{subtitle}</p>}
          </div>
          {bannerImage && (
            <div className="listing-banner-img" aria-hidden="true">
              <img src={bannerImage} alt="" />
            </div>
          )}
        </header>

        <div className="listing-toolbar">
          <div className="filter-row" role="group" aria-label={t('products.filters')}>
            <FilterPill label={t('products.bodyPart')} count={injuryType ? 1 : 0}>
              {({ close }) => (
                <div className="filter-options">
                  {BODY_PARTS.map((p) => (
                    <button
                      key={p.key}
                      type="button"
                      className={`chip ${injuryType === p.key ? 'active' : ''}`}
                      onClick={() => {
                        updateParams({ injury_type: injuryType === p.key ? '' : p.key });
                        close();
                      }}
                    >
                      {lang === 'fa' ? p.fa : p.en}
                    </button>
                  ))}
                </div>
              )}
            </FilterPill>

            {sports.length > 0 && (
              <FilterPill label={t('products.sport', 'ورزش')} count={sport ? 1 : 0}>
                {({ close }) => (
                  <div className="filter-options">
                    {sports.map((s) => (
                      <button
                        key={s.slug}
                        type="button"
                        className={`chip ${sport === s.slug ? 'active' : ''}`}
                        onClick={() => {
                          updateParams({ sport: sport === s.slug ? '' : s.slug });
                          close();
                        }}
                      >
                        {sportName(s, lang)}
                      </button>
                    ))}
                  </div>
                )}
              </FilterPill>
            )}

            <FilterPill label={t('products.category')} count={category ? 1 : 0}>
              {({ close }) => (
                <ul className="filter-list">
                  {categories.map((c) => (
                    <li key={c.id}>
                      <label className="radio-row">
                        <input
                          type="radio"
                          name="category"
                          checked={category === c.slug}
                          onChange={() => {
                            updateParams({ category: c.slug });
                            close();
                          }}
                        />
                        <span>{(lang === 'fa' && c.name_fa) || c.name}</span>
                        <small>{num(c.product_count)}</small>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </FilterPill>

            <FilterPill label={t('products.priceRange')} count={minPrice || maxPrice ? 1 : 0}>
              {({ close }) => (
                <form
                  className="price-filter"
                  onSubmit={(e) => {
                    e.preventDefault();
                    updateParams({ min_price: priceDraft.min, max_price: priceDraft.max });
                    close();
                  }}
                >
                  <label>
                    <span>{t('products.minPrice', 'از (تومان)')}</span>
                    <input
                      type="number"
                      min="0"
                      inputMode="numeric"
                      value={priceDraft.min}
                      onChange={(e) => setPriceDraft((d) => ({ ...d, min: e.target.value }))}
                      className="form-input"
                    />
                  </label>
                  <label>
                    <span>{t('products.maxPrice', 'تا (تومان)')}</span>
                    <input
                      type="number"
                      min="0"
                      inputMode="numeric"
                      value={priceDraft.max}
                      onChange={(e) => setPriceDraft((d) => ({ ...d, max: e.target.value }))}
                      className="form-input"
                    />
                  </label>
                  <button type="submit" className="btn btn-primary btn-sm btn-full">{t('products.apply', 'اعمال')}</button>
                </form>
              )}
            </FilterPill>

            <FilterPill label={t('products.availability', 'موجودی و تخفیف')} count={(inStock ? 1 : 0) + (onSale ? 1 : 0)}>
              {() => (
                <div className="filter-list">
                  <label className="check-row">
                    <input
                      type="checkbox"
                      checked={inStock === 'true'}
                      onChange={(e) => updateParams({ in_stock: e.target.checked ? 'true' : '' })}
                    />
                    <span>{t('products.inStockOnly')}</span>
                  </label>
                  <label className="check-row">
                    <input
                      type="checkbox"
                      checked={onSale === 'true'}
                      onChange={(e) => updateParams({ on_sale: e.target.checked ? 'true' : '' })}
                    />
                    <span>{t('products.onSaleOnly', 'فقط کالاهای تخفیف‌دار')}</span>
                  </label>
                </div>
              )}
            </FilterPill>
          </div>

          <div className="sort-box">
            <span className="result-count" aria-live="polite">
              {loading ? '' : t('products.productsCount', { count: num(totalCount) })}
            </span>
            <label className="sort-select-wrap">
              <span className="sr-only">{t('products.sortBy')}</span>
              <select value={ordering} onChange={(e) => updateParams({ ordering: e.target.value })} className="sort-select">
                {sortOptions.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <Icon name="chevronDown" size={16} />
            </label>
          </div>
        </div>

        {activeChips.length > 0 && (
          <div className="active-chips">
            {activeChips.map((chip) => (
              <button key={chip.key} type="button" className="chip active" onClick={() => removeChip(chip.key)}>
                {chip.label}
                <Icon name="close" size={14} />
              </button>
            ))}
            <button type="button" className="clear-link" onClick={clearFilters}>{t('common.clearAll')}</button>
          </div>
        )}

        {loading ? (
          <div className="product-grid">
            {Array.from({ length: 8 }).map((_, i) => <ProductCardSkeleton key={i} />)}
          </div>
        ) : products.length === 0 ? (
          <div className="empty-panel">
            <Icon name="search" size={40} strokeWidth={1.4} />
            <h2>{t('products.noProductsFound')}</h2>
            <p>{t('products.noProductsDesc')}</p>
            <div className="empty-actions">
              <button onClick={clearFilters} className="btn btn-primary">{t('products.clearFilters')}</button>
              <Link to="/products" className="btn btn-outline">{t('products.allProducts')}</Link>
            </div>
          </div>
        ) : (
          <>
            <div className="product-grid">
              {products.map((product) => <ProductCard key={product.id} product={product} />)}
            </div>

            {totalPages > 1 && (
              <nav className="pagination" aria-label={t('products.pagination', 'صفحه‌بندی')}>
                <button className="page-btn" disabled={page === 1} onClick={() => goToPage(page - 1)} aria-label={t('products.previous')}>
                  <Icon name="chevronRight" size={18} className="flip-ltr" />
                </button>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                  <button
                    key={p}
                    className={`page-btn ${p === page ? 'active' : ''}`}
                    aria-current={p === page ? 'page' : undefined}
                    onClick={() => goToPage(p)}
                  >
                    {num(p)}
                  </button>
                ))}
                <button className="page-btn" disabled={page === totalPages} onClick={() => goToPage(page + 1)} aria-label={t('products.next')}>
                  <Icon name="chevronLeft" size={18} className="flip-ltr" />
                </button>
              </nav>
            )}
          </>
        )}
      </div>
    </div>
  );
}
