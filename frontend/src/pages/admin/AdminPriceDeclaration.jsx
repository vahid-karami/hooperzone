import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import apiClient from '../../api/client';
import { ENDPOINTS } from '../../api/endpoints';
import { useToast } from '../../context/ToastContext';
import Price from '../../components/Price';
import Icon from '../../components/Icon';
import { useCategories } from '../../utils/catalog';
import { fetchAllPages } from '../../utils/fetchAll';
import { toEnglishDigits } from '../../utils/digits';
import { toPersianNumber } from '../../hooks/useLanguage';
import { usePageMeta } from '../../utils/seo';

// Mirrors products.views.bulk_price_update: round to 1,000 Toman, never down to zero.
function adjust(price, pct) {
  const next = Number(price) * (1 + pct / 100);
  const rounded = Math.round(next / 1000) * 1000;
  return rounded > 0 ? rounded : Math.round(next * 100) / 100;
}

export default function AdminPriceDeclaration() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const { success, error: showError } = useToast();
  const categories = useCategories();
  const [products, setProducts] = useState(null);
  const [categoryId, setCategoryId] = useState('');
  const [percentage, setPercentage] = useState('');
  const [applying, setApplying] = useState(false);

  usePageMeta({ title: t('admin.priceList', 'اعلامیه قیمت'), noindex: true });

  const load = useCallback(() => {
    fetchAllPages(ENDPOINTS.adminProducts)
      .then(setProducts)
      .catch(() => setProducts([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const pct = parseFloat(toEnglishDigits(percentage));
  const validPct = Number.isFinite(pct) && pct > -100 && pct !== 0;
  const category = categories.find((c) => String(c.id) === categoryId);
  const rows = (products || []).filter((p) => !categoryId || String(p.category) === categoryId);

  const handleApply = async () => {
    if (!validPct) return;
    const scope = category ? `«${category.name_fa || category.name}»` : t('admin.allProducts', 'همه محصولات');
    if (!window.confirm(t('admin.applyConfirm', 'قیمت {{scope}} {{pct}}٪ تغییر کند؟', { scope, pct: num(pct) }))) return;
    setApplying(true);
    try {
      const { data } = await apiClient.post(ENDPOINTS.adminBulkPriceUpdate, { category_id: categoryId || null, percentage: pct });
      success(t('admin.pricesUpdated', 'قیمت {{count}} محصول به‌روز شد', { count: num(data.updated_count) }));
      setPercentage('');
      load();
    } catch (err) {
      showError(err.response?.data?.error || t('admin.updateFailed', 'به‌روزرسانی انجام نشد'));
    } finally {
      setApplying(false);
    }
  };

  const today = new Intl.DateTimeFormat(lang === 'fa' ? 'fa-IR' : 'en-US', { dateStyle: 'long' }).format(new Date());

  return (
    <div className="admin-page price-list-page">
      <header className="admin-page-head hide-on-print">
        <div>
          <h1>{t('admin.priceList', 'اعلامیه قیمت')}</h1>
          <p className="muted">{t('admin.priceListHint', 'تغییر گروهی قیمت‌ها و چاپ فهرست قیمت برای فروشگاه')}</p>
        </div>
        <button onClick={() => window.print()} className="btn btn-outline">
          <Icon name="box" size={18} /> {t('admin.print', 'چاپ فهرست قیمت')}
        </button>
      </header>

      <section className="admin-card hide-on-print">
        <div className="form-grid">
          <div className="form-group">
            <label className="form-label" htmlFor="pl-category">{t('product.category')}</label>
            <select id="pl-category" value={categoryId} onChange={(e) => setCategoryId(e.target.value)} className="form-select">
              <option value="">{t('admin.allProducts', 'همه محصولات')}</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name_fa || c.name}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="pl-pct">{t('admin.changePercent', 'درصد تغییر')}</label>
            <input
              id="pl-pct"
              value={percentage}
              onChange={(e) => setPercentage(e.target.value)}
              className="form-input"
              inputMode="decimal"
              dir="ltr"
              placeholder="+15 / -10"
            />
          </div>
          <div className="form-group apply-cell">
            <button onClick={handleApply} disabled={!validPct || applying} className="btn btn-primary btn-full">
              {applying ? t('common.loading') : t('admin.applyPrices', 'اعمال روی {{count}} محصول', { count: num(rows.length) })}
            </button>
          </div>
        </div>
        <p className="muted card-hint">
          {t('admin.pctHint', 'عدد مثبت برای افزایش و منفی برای کاهش قیمت. قیمت‌ها به نزدیک‌ترین ۱٬۰۰۰ تومان گرد می‌شوند. ستون «قیمت جدید» پیش‌نمایش است و تا زمان اعمال ذخیره نمی‌شود.')}
        </p>
      </section>

      <div className="print-only print-title">
        <h2>{t('admin.printTitle', 'فهرست قیمت محصولات هوپرزون')}</h2>
        <p>{today}{category ? ` — ${category.name_fa || category.name}` : ''}</p>
      </div>

      <section className="admin-card flush">
        {products === null ? (
          <div className="loading"><div className="spinner" /></div>
        ) : (
          <div className="table-wrap">
            <table className="data-table price-table">
              <thead>
                <tr>
                  <th>{t('admin.product', 'محصول')}</th>
                  <th>{t('product.category')}</th>
                  <th>{t('admin.currentPrice', 'قیمت فعلی')}</th>
                  {validPct && <th className="hide-on-print">{t('admin.newPrice', 'قیمت جدید')}</th>}
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.id}>
                    <td>{p.name_fa || p.name}</td>
                    <td>{p.category_name_fa || p.category_name}</td>
                    <td><Price amount={p.price} /></td>
                    {validPct && (
                      <td className={`hide-on-print ${pct > 0 ? 'text-ok' : 'text-bad'}`}>
                        <strong><Price amount={adjust(p.price, pct)} /></strong>
                      </td>
                    )}
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr><td colSpan={4} className="muted">{t('products.noProductsFound')}</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
