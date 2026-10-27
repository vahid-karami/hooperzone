import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import apiClient from '../../api/client';
import { ENDPOINTS } from '../../api/endpoints';
import { useToast } from '../../context/ToastContext';
import Price from '../../components/Price';
import Icon from '../../components/Icon';
import AdminPager from '../../components/admin/AdminPager';
import { BODY_PARTS } from '../../utils/bodyParts';
import { downloadFile } from '../../utils/download';
import { toPersianNumber } from '../../hooks/useLanguage';
import { usePageMeta } from '../../utils/seo';

const PAGE_SIZE = 25;

// Filter tabs map to the admin API's query parameters.
const TAB_PARAMS = {
  all: {},
  active: { is_active: 'true' },
  inactive: { is_active: 'false' },
  out: { in_stock: 'false' },
  low: { low_stock: 'true' },
  featured: { is_featured: 'true' },
};

function ImageManager({ product, onChange }) {
  const { t } = useTranslation();
  const { error: showError } = useToast();
  const [images, setImages] = useState(product.images || []);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);

  const apply = (list) => {
    setImages(list);
    onChange(list);
  };

  const upload = async (files) => {
    const list = [...files].filter((f) => f.type.startsWith('image/'));
    if (!list.length) return;
    setBusy(true);
    try {
      let latest = images;
      for (const file of list) {
        const body = new FormData();
        body.append('image', file);
        const res = await apiClient.post(ENDPOINTS.adminProductImages(product.slug), body);
        latest = res.data;
      }
      apply(latest);
    } catch (err) {
      showError(err.response?.data?.error || err.response?.data?.image?.[0] || t('admin.uploadFailed', 'آپلود تصویر انجام نشد'));
    } finally {
      setBusy(false);
    }
  };

  const update = async (img, payload) => {
    try {
      const res = await apiClient.patch(ENDPOINTS.adminProductImage(product.slug, img.id), payload);
      apply(res.data);
    } catch {
      showError(t('admin.updateFailed', 'به‌روزرسانی انجام نشد'));
    }
  };

  const remove = async (img) => {
    if (!window.confirm(t('admin.deleteImageConfirm', 'این تصویر حذف شود؟'))) return;
    try {
      const res = await apiClient.delete(ENDPOINTS.adminProductImage(product.slug, img.id));
      apply(res.data);
    } catch {
      showError(t('admin.deleteFailed', 'حذف انجام نشد'));
    }
  };

  return (
    <fieldset>
      <legend>{t('admin.images', 'تصاویر')}</legend>
      <div className="image-manager">
        {images.map((img) => (
          <figure key={img.id} className={`image-item ${img.is_primary ? 'is-primary' : ''}`}>
            <img src={img.image} alt={img.alt_text} loading="lazy" />
            {img.is_primary && <span className="status-pill tone-ok image-badge">{t('admin.primaryImage', 'تصویر اصلی')}</span>}
            <figcaption>
              <input
                className="form-input"
                defaultValue={img.alt_text}
                aria-label={t('admin.altText', 'متن جایگزین (سئو)')}
                placeholder={t('admin.altText', 'متن جایگزین (سئو)')}
                onBlur={(e) => e.target.value !== img.alt_text && update(img, { alt_text: e.target.value })}
              />
              <div className="image-actions">
                {!img.is_primary && (
                  <button type="button" className="text-btn" onClick={() => update(img, { is_primary: 'true' })}>
                    {t('admin.makePrimary', 'تصویر اصلی شود')}
                  </button>
                )}
                <button type="button" className="icon-btn danger-btn" onClick={() => remove(img)} aria-label={t('admin.delete', 'حذف')}>
                  <Icon name="trash" size={16} />
                </button>
              </div>
            </figcaption>
          </figure>
        ))}
        <label
          className={`image-drop small ${dragging ? 'is-dragging' : ''}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            upload(e.dataTransfer.files);
          }}
        >
          <span>
            <Icon name="upload" size={26} />
            {busy ? t('admin.uploading', 'در حال آپلود…') : t('admin.addImages', 'افزودن تصویر (کشیدن و رها کردن)')}
          </span>
          <input type="file" accept="image/*" multiple disabled={busy} onChange={(e) => upload(e.target.files)} />
        </label>
      </div>
    </fieldset>
  );
}

const EMPTY_FORM = {
  name: '', name_fa: '', description: '', description_fa: '', category: '',
  price: '', cost: '', discount_price: '', stock: '', injury_type: 'general',
  brand: '', size: '', color: '', weight: '', material: '', is_active: true, is_featured: false, sports: [],
};

const toNumberOrNull = (v, parse = parseFloat) => (v === '' || v === null || v === undefined ? null : parse(v));

export default function AdminProducts() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const { success, error: showError } = useToast();
  const [categories, setCategories] = useState([]);
  const [sports, setSports] = useState([]);
  const [data, setData] = useState(null);
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [tab, setTab] = useState('all');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState(() => new Set());
  const [editing, setEditing] = useState(null); // null = closed, {} = new, product = edit
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const debounce = useRef();

  usePageMeta({ title: t('admin.products', 'محصولات'), noindex: true });

  useEffect(() => {
    apiClient.get(ENDPOINTS.adminCategories).then((r) => setCategories(r.data.results || r.data)).catch(() => {});
    apiClient.get(ENDPOINTS.sports).then((r) => setSports(r.data.results || r.data)).catch(() => {});
  }, []);

  // Search as the user types, without a request per keystroke.
  useEffect(() => {
    clearTimeout(debounce.current);
    debounce.current = setTimeout(() => {
      setSearch(query.trim());
      setPage(1);
    }, 300);
    return () => clearTimeout(debounce.current);
  }, [query]);

  const listParams = useCallback(
    () => ({ ...TAB_PARAMS[tab], search: search || undefined }),
    [tab, search],
  );

  const load = useCallback(() => {
    apiClient
      .get(ENDPOINTS.adminProducts, { params: { ...listParams(), page, page_size: PAGE_SIZE } })
      .then((res) => setData(res.data))
      .catch(() => {
        setData({ count: 0, results: [] });
        showError(t('admin.loadFailed', 'بارگذاری اطلاعات انجام نشد'));
      });
  }, [listParams, page, showError, t]);

  useEffect(() => {
    setSelected(new Set());
    load();
  }, [load]);

  const products = data?.results;

  const tabs = [
    { key: 'all', label: t('orders.all', 'همه') },
    { key: 'active', label: t('admin.active', 'فعال') },
    { key: 'inactive', label: t('admin.inactive', 'غیرفعال') },
    { key: 'out', label: t('common.outOfStock') },
    { key: 'low', label: t('admin.lowStockTab', 'کم‌موجود') },
    { key: 'featured', label: t('product.bestseller', 'پرفروش') },
  ];

  const replaceProduct = (updated) =>
    setData((d) => (d ? { ...d, results: d.results.map((p) => (p.id === updated.id ? updated : p)) } : d));

  const quickStock = async (p, value) => {
    const stock = parseInt(value, 10);
    if (Number.isNaN(stock) || stock < 0 || stock === p.stock) return;
    try {
      const res = await apiClient.patch(ENDPOINTS.adminProductDetail(p.slug), { stock });
      replaceProduct(res.data);
      success(t('admin.stockSaved', 'موجودی به‌روز شد'));
    } catch {
      showError(t('admin.updateFailed', 'به‌روزرسانی انجام نشد'));
    }
  };

  const bulk = async (action) => {
    const slugs = [...selected];
    if (action === 'delete' && !window.confirm(t('admin.bulkDeleteConfirm', '{{count}} محصول حذف شود؟ محصولاتی که سفارش داشته‌اند فقط غیرفعال می‌شوند.', { count: num(slugs.length) }))) return;
    try {
      await apiClient.post(ENDPOINTS.adminProductBulkAction, { slugs, action });
      success(t('admin.bulkDone', 'انجام شد'));
      load();
    } catch (err) {
      showError(err.response?.data?.error || t('admin.updateFailed', 'به‌روزرسانی انجام نشد'));
    }
  };

  const allSelected = products?.length > 0 && products.every((p) => selected.has(p.slug));
  const toggleAll = () => setSelected(allSelected ? new Set() : new Set(products.map((p) => p.slug)));
  const toggleOne = (slug) =>
    setSelected((s0) => {
      const next = new Set(s0);
      if (next.has(slug)) next.delete(slug);
      else next.add(slug);
      return next;
    });

  const openNew = () => {
    setForm(EMPTY_FORM);
    setFormError('');
    setEditing({});
  };

  const openEdit = (p) => {
    setForm({
      ...EMPTY_FORM,
      ...Object.fromEntries(Object.keys(EMPTY_FORM).map((k) => [k, p[k] ?? EMPTY_FORM[k]])),
      category: p.category ?? '',
      price: p.price != null ? String(Number(p.price)) : '',
      cost: p.cost != null ? String(Number(p.cost)) : '',
      discount_price: p.discount_price != null ? String(Number(p.discount_price)) : '',
      weight: p.weight != null ? String(Number(p.weight)) : '',
      stock: String(p.stock ?? ''),
      sports: p.sports || [],
    });
    setFormError('');
    setEditing(p);
  };

  const setField = (name, value) => setForm((f) => ({ ...f, [name]: value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setFormError('');
    const payload = {
      ...form,
      category: form.category ? parseInt(form.category, 10) : null,
      price: toNumberOrNull(form.price) ?? 0,
      cost: toNumberOrNull(form.cost),
      discount_price: toNumberOrNull(form.discount_price),
      stock: parseInt(form.stock, 10) || 0,
      weight: toNumberOrNull(form.weight),
    };
    try {
      if (editing?.slug) {
        await apiClient.patch(ENDPOINTS.adminProductDetail(editing.slug), payload);
        success(t('admin.productUpdated', 'محصول به‌روز شد'));
        setEditing(null);
      } else {
        // Keep the dialog open on the new product so its photos can be added right away.
        const res = await apiClient.post(ENDPOINTS.adminProducts, payload);
        success(t('admin.productCreatedAddImages', 'محصول ایجاد شد؛ حالا تصاویر را اضافه کنید'));
        setEditing(res.data);
      }
      load();
    } catch (err) {
      const data = err.response?.data;
      const fieldErrors = data && typeof data === 'object' && !data.error
        ? Object.entries(data).map(([field, msgs]) => `${field}: ${[].concat(msgs).join(' ')}`).join(' — ')
        : '';
      setFormError(data?.error || fieldErrors || t('admin.saveFailed', 'ذخیره محصول انجام نشد'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (p) => {
    if (!window.confirm(t('admin.deleteConfirm', '«{{name}}» حذف شود؟ این کار برگشت‌پذیر نیست.', { name: p.name_fa || p.name }))) return;
    try {
      await apiClient.delete(ENDPOINTS.adminProductDetail(p.slug));
      success(t('admin.productDeleted', 'محصول حذف شد'));
      load();
    } catch (err) {
      showError(err.response?.data?.detail || t('admin.deleteFailed', 'حذف انجام نشد (ممکن است در سفارشی استفاده شده باشد).'));
    }
  };

  const input = (name, label, props = {}) => (
    <div className="form-group">
      <label className="form-label" htmlFor={`p-${name}`}>{label}</label>
      <input id={`p-${name}`} value={form[name]} onChange={(e) => setField(name, e.target.value)} className="form-input" {...props} />
    </div>
  );

  return (
    <div className="admin-page">
      <header className="admin-page-head">
        <div>
          <h1>{t('admin.products', 'محصولات')}</h1>
          <p className="muted">
            {data ? t('admin.productsCount', '{{count}} محصول در فروشگاه', { count: num(data.count) }) : t('common.loading')}
          </p>
        </div>
        <div className="admin-head-actions">
          <div className="admin-search">
            <Icon name="search" size={18} />
            <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('admin.searchProducts', 'جستجوی نام، برند یا کد')} aria-label={t('common.search')} />
          </div>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => downloadFile(ENDPOINTS.adminProductExport, listParams(), 'products.csv').catch(() => showError(t('admin.exportFailed', 'دریافت فایل انجام نشد')))}
          >
            <Icon name="download" size={18} /> {t('admin.exportCsv', 'خروجی اکسل')}
          </button>
          <button onClick={openNew} className="btn btn-primary">
            <Icon name="plus" size={18} /> {t('admin.addProduct', 'محصول جدید')}
          </button>
        </div>
      </header>

      <div className="tab-row" role="tablist">
        {tabs.map((x) => (
          <button
            key={x.key}
            role="tab"
            aria-selected={tab === x.key}
            className={`tab ${tab === x.key ? 'active' : ''}`}
            onClick={() => {
              setTab(x.key);
              setPage(1);
            }}
          >
            {x.label}
          </button>
        ))}
      </div>

      {selected.size > 0 && (
        <div className="bulk-bar" role="region" aria-label={t('admin.bulkActions', 'عملیات گروهی')}>
          <strong>{t('admin.selectedCount', '{{count}} مورد انتخاب شده', { count: num(selected.size) })}</strong>
          <button className="btn btn-outline btn-sm" onClick={() => bulk('activate')}>{t('admin.activate', 'فعال کردن')}</button>
          <button className="btn btn-outline btn-sm" onClick={() => bulk('deactivate')}>{t('admin.deactivate', 'غیرفعال کردن')}</button>
          <button className="btn btn-outline btn-sm" onClick={() => bulk('feature')}>{t('admin.feature', 'افزودن به پرفروش‌ها')}</button>
          <button className="btn btn-outline btn-sm" onClick={() => bulk('unfeature')}>{t('admin.unfeature', 'حذف از پرفروش‌ها')}</button>
          <button className="btn btn-outline btn-sm danger-btn" onClick={() => bulk('delete')}>{t('admin.delete', 'حذف')}</button>
          <button className="text-btn" onClick={() => setSelected(new Set())}>{t('admin.cancel', 'انصراف')}</button>
        </div>
      )}

      <section className="admin-card flush">
        {data === null ? (
          <div className="loading"><div className="spinner" /></div>
        ) : products.length === 0 ? (
          <p className="muted empty-inline">{t('products.noProductsFound')}</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="check-col">
                    <input type="checkbox" checked={allSelected} onChange={toggleAll} aria-label={t('admin.selectAll', 'انتخاب همه')} />
                  </th>
                  <th>{t('admin.product', 'محصول')}</th>
                  <th>{t('product.category')}</th>
                  <th>{t('common.price')}</th>
                  <th>{t('admin.margin', 'سود')}</th>
                  <th>{t('admin.stock', 'موجودی')}</th>
                  <th>{t('admin.status', 'وضعیت')}</th>
                  <th><span className="sr-only">{t('admin.actions', 'عملیات')}</span></th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => {
                  const discounted = p.discount_price && Number(p.discount_price) < Number(p.price);
                  return (
                    <tr key={p.id} className={`${p.is_active ? '' : 'is-muted'} ${selected.has(p.slug) ? 'is-selected' : ''}`}>
                      <td className="check-col">
                        <input type="checkbox" checked={selected.has(p.slug)} onChange={() => toggleOne(p.slug)} aria-label={p.name_fa || p.name} />
                      </td>
                      <td>
                        <div className="product-cell">
                          <span className="product-thumb">
                            {p.primary_image ? <img src={p.primary_image} alt="" loading="lazy" /> : <Icon name="image" size={20} />}
                          </span>
                          <div className="cell-stack">
                            <strong>{p.name_fa || p.name}</strong>
                            <span className="muted">{p.brand || '—'}</span>
                          </div>
                        </div>
                      </td>
                      <td>{p.category_name_fa || p.category_name || '—'}</td>
                      <td>
                        <div className="cell-stack">
                          <Price amount={discounted ? p.discount_price : p.price} />
                          {discounted && <span className="price-was"><Price amount={p.price} showSymbol={false} /></span>}
                        </div>
                      </td>
                      <td>
                        {p.margin != null ? (
                          <span className={p.margin >= 0 ? 'text-ok' : 'text-bad'}>{num(p.margin_percent)}٪</span>
                        ) : '—'}
                      </td>
                      <td>
                        <input
                          key={`${p.id}-${p.stock}`}
                          className={`stock-input ${p.stock === 0 ? 'tone-bad' : p.stock <= 5 ? 'tone-warn' : 'tone-ok'}`}
                          type="number"
                          min={0}
                          dir="ltr"
                          defaultValue={p.stock}
                          aria-label={t('admin.stock', 'موجودی')}
                          onBlur={(e) => quickStock(p, e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
                        />
                      </td>
                      <td>
                        <div className="order-badges">
                          <span className={`status-pill ${p.is_active ? 'tone-info' : 'tone-bad'}`}>{p.is_active ? t('admin.active', 'فعال') : t('admin.inactive', 'غیرفعال')}</span>
                          {p.is_featured && <span className="status-pill tone-ok">{t('product.bestseller', 'پرفروش')}</span>}
                        </div>
                      </td>
                      <td>
                        <div className="row-actions">
                          <button className="icon-btn" onClick={() => openEdit(p)} aria-label={t('admin.edit', 'ویرایش')} title={t('admin.edit', 'ویرایش')}>
                            <Icon name="edit" size={18} />
                          </button>
                          <a
                            className="icon-btn"
                            href={`/products/${p.slug}`}
                            target="_blank"
                            rel="noreferrer"
                            aria-label={t('admin.viewInShop', 'نمایش در فروشگاه')}
                            title={t('admin.viewInShop', 'نمایش در فروشگاه')}
                          >
                            <Icon name="search" size={18} />
                          </a>
                          <button className="icon-btn danger-btn" onClick={() => handleDelete(p)} aria-label={t('admin.delete', 'حذف')} title={t('admin.delete', 'حذف')}>
                            <Icon name="trash" size={18} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {data && <AdminPager page={page} pageSize={PAGE_SIZE} count={data.count} onChange={setPage} />}

      {editing && (
        <div className="modal-overlay" onClick={() => setEditing(null)}>
          <div className="modal modal-lg" role="dialog" aria-modal="true" aria-labelledby="product-form-title" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 id="product-form-title">{editing.slug ? t('admin.editProduct', 'ویرایش محصول') : t('admin.addProduct', 'محصول جدید')}</h2>
              <button onClick={() => setEditing(null)} className="icon-btn" aria-label={t('common.close', 'بستن')}><Icon name="close" /></button>
            </div>
            <form onSubmit={handleSubmit} className="admin-form">
              {formError && <p className="form-alert">{formError}</p>}

              <fieldset>
                <legend>{t('admin.basicInfo', 'اطلاعات اصلی')}</legend>
                <div className="form-grid two">
                  {input('name_fa', t('admin.nameFa', 'نام فارسی'), { required: true })}
                  {input('name', t('admin.nameEn', 'نام انگلیسی'), { dir: 'ltr', required: true })}
                  <div className="form-group">
                    <label className="form-label" htmlFor="p-category">{t('product.category')}</label>
                    <select id="p-category" value={form.category} onChange={(e) => setField('category', e.target.value)} className="form-select" required>
                      <option value="">{t('admin.selectCategory', 'انتخاب دسته‌بندی')}</option>
                      {categories.map((c) => <option key={c.id} value={c.id}>{c.name_fa || c.name}</option>)}
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label" htmlFor="p-injury">{t('products.bodyPart')}</label>
                    <select id="p-injury" value={form.injury_type} onChange={(e) => setField('injury_type', e.target.value)} className="form-select">
                      {BODY_PARTS.map((b) => <option key={b.key} value={b.key}>{lang === 'fa' ? b.fa : b.en}</option>)}
                    </select>
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="p-desc-fa">{t('admin.descFa', 'توضیحات فارسی')}</label>
                  <textarea id="p-desc-fa" value={form.description_fa} onChange={(e) => setField('description_fa', e.target.value)} className="form-textarea" rows={3} />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="p-desc">{t('admin.descEn', 'توضیحات انگلیسی')}</label>
                  <textarea id="p-desc" value={form.description} onChange={(e) => setField('description', e.target.value)} className="form-textarea" rows={2} dir="ltr" required />
                </div>
              </fieldset>

              <fieldset>
                <legend>{t('admin.pricing', 'قیمت و موجودی (تومان)')}</legend>
                <div className="form-grid">
                  {input('price', t('admin.price', 'قیمت فروش'), { type: 'number', min: 0, step: 1000, dir: 'ltr', required: true })}
                  {input('discount_price', t('admin.discountPrice', 'قیمت با تخفیف'), { type: 'number', min: 0, step: 1000, dir: 'ltr' })}
                  {input('cost', t('admin.cost', 'قیمت خرید'), { type: 'number', min: 0, step: 1000, dir: 'ltr' })}
                  {input('stock', t('admin.stock', 'موجودی'), { type: 'number', min: 0, dir: 'ltr', required: true })}
                </div>
              </fieldset>

              <fieldset>
                <legend>{t('product.specifications')}</legend>
                <div className="form-grid">
                  {input('brand', t('product.brand', 'برند'))}
                  {input('size', t('product.size'))}
                  {input('color', t('product.color'))}
                  {input('material', t('product.material'))}
                  {input('weight', t('admin.weight', 'وزن (گرم)'), { type: 'number', min: 0, dir: 'ltr' })}
                </div>
                {sports.length > 0 && (
                  <div className="form-group">
                    <span className="form-label">{t('admin.sports', 'رشته‌های ورزشی')}</span>
                    <div className="chip-picker">
                      {sports.map((sp) => {
                        const on = form.sports.includes(sp.id);
                        return (
                          <button
                            type="button"
                            key={sp.id}
                            className={`chip ${on ? 'active' : ''}`}
                            aria-pressed={on}
                            onClick={() => setField('sports', on ? form.sports.filter((id) => id !== sp.id) : [...form.sports, sp.id])}
                          >
                            {lang === 'fa' ? sp.name_fa || sp.name : sp.name}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
                <div className="switch-row">
                  <label className="check-inline">
                    <input type="checkbox" checked={form.is_active} onChange={(e) => setField('is_active', e.target.checked)} />
                    {t('admin.activeHint', 'نمایش در فروشگاه')}
                  </label>
                  <label className="check-inline">
                    <input type="checkbox" checked={form.is_featured} onChange={(e) => setField('is_featured', e.target.checked)} />
                    {t('admin.featuredHint', 'نمایش در پرفروش‌ها')}
                  </label>
                </div>
              </fieldset>

              {editing.slug ? (
                <ImageManager
                  key={editing.slug}
                  product={editing}
                  onChange={(images) => replaceProduct({ ...editing, images, primary_image: images[0]?.image || null })}
                />
              ) : (
                <p className="field-hint">{t('admin.imagesAfterSave', 'پس از ذخیره محصول می‌توانید تصاویر را اضافه کنید.')}</p>
              )}

              <div className="modal-actions">
                <button type="button" onClick={() => setEditing(null)} className="btn btn-outline">{t('admin.cancel', 'انصراف')}</button>
                <button type="submit" disabled={saving} className="btn btn-primary">
                  {saving ? t('common.loading') : t('admin.save', 'ذخیره')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
