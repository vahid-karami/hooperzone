import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../../api/client';
import { ENDPOINTS } from '../../api/endpoints';
import { useToast } from '../../context/ToastContext';
import Price from '../../components/Price';
import Icon from '../../components/Icon';
import AdminPager from '../../components/admin/AdminPager';
import { formatDate } from '../../utils/persianDate';
import { downloadFile } from '../../utils/download';
import { toEnglishDigits } from '../../utils/digits';
import { toPersianNumber } from '../../hooks/useLanguage';
import { usePageMeta } from '../../utils/seo';

const PAGE_SIZE = 25;

export default function AdminCustomers() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const { error: showError } = useToast();
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [search, setSearch] = useState(params.get('search') || '');

  const searchParam = params.get('search') || '';
  const sort = params.get('sort') || 'recent';
  const hasOrders = params.get('has_orders') === 'true';
  const page = Number(params.get('page')) || 1;

  usePageMeta({ title: t('admin.customersTitle', 'مشتریان'), noindex: true });

  const query = { search: searchParam || undefined, sort, has_orders: hasOrders ? 'true' : undefined };

  useEffect(() => {
    let active = true;
    setData(null);
    apiClient
      .get(ENDPOINTS.adminCustomers, { params: { search: searchParam || undefined, sort, has_orders: hasOrders ? 'true' : undefined, page, page_size: PAGE_SIZE } })
      .then((res) => active && setData(res.data))
      .catch(() => active && setData({ count: 0, results: [] }));
    return () => {
      active = false;
    };
  }, [searchParam, sort, hasOrders, page]);

  const setFilter = (changes) => {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    if (!('page' in changes)) next.delete('page');
    setParams(next);
  };

  const sorts = [
    { key: 'recent', label: t('admin.sortRecent', 'جدیدترین') },
    { key: 'spent', label: t('admin.sortSpent', 'بیشترین خرید') },
    { key: 'orders', label: t('admin.sortOrders', 'بیشترین سفارش') },
    { key: 'last_order', label: t('admin.sortLastOrder', 'آخرین سفارش') },
  ];

  return (
    <div className="admin-page">
      <header className="admin-page-head">
        <div>
          <h1>{t('admin.customersTitle', 'مشتریان')}</h1>
          <p className="muted">{data ? t('admin.customersFound', '{{count}} مشتری', { count: num(data.count) }) : t('common.loading')}</p>
        </div>
        <div className="admin-head-actions">
          <form
            className="admin-search"
            role="search"
            onSubmit={(e) => {
              e.preventDefault();
              setFilter({ search: toEnglishDigits(search.trim()) });
            }}
          >
            <Icon name="search" size={18} />
            <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t('admin.searchCustomers', 'نام، موبایل یا ایمیل')} aria-label={t('common.search')} />
          </form>
          <button
            type="button"
            className="btn btn-outline"
            onClick={() => downloadFile(ENDPOINTS.adminCustomersExport, query, 'customers.csv').catch(() => showError(t('admin.exportFailed', 'دریافت فایل انجام نشد')))}
          >
            <Icon name="download" size={18} /> {t('admin.exportCsv', 'خروجی اکسل')}
          </button>
        </div>
      </header>

      <div className="tab-row" role="tablist">
        {sorts.map((s) => (
          <button key={s.key} role="tab" aria-selected={sort === s.key} className={`tab ${sort === s.key ? 'active' : ''}`} onClick={() => setFilter({ sort: s.key })}>
            {s.label}
          </button>
        ))}
        <label className="check-inline">
          <input type="checkbox" checked={hasOrders} onChange={(e) => setFilter({ has_orders: e.target.checked ? 'true' : '' })} />
          {t('admin.withOrdersOnly', 'فقط خریداران')}
        </label>
      </div>

      <section className="admin-card flush">
        {data === null ? (
          <div className="loading"><div className="spinner" /></div>
        ) : data.results.length === 0 ? (
          <p className="muted empty-inline">{t('admin.noCustomers', 'مشتری‌ای پیدا نشد.')}</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('admin.customer', 'مشتری')}</th>
                  <th>{t('profile.city', 'شهر')}</th>
                  <th>{t('admin.joined', 'عضویت')}</th>
                  <th>{t('admin.orders', 'سفارش‌ها')}</th>
                  <th>{t('admin.totalSpent', 'مجموع خرید')}</th>
                  <th>{t('admin.lastOrder', 'آخرین سفارش')}</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((c) => (
                  <tr key={c.id}>
                    <td>
                      <div className="cell-stack">
                        <strong>{c.name || '—'} {c.is_verified && <Icon name="checkCircle" size={14} className="text-ok" aria-label={t('admin.verified', 'تأیید شده')} />}</strong>
                        <span dir="ltr">{num(c.phone || '')}</span>
                        {c.email && <span className="muted" dir="ltr">{c.email}</span>}
                      </div>
                    </td>
                    <td>{[c.province, c.city].filter(Boolean).join('، ') || '—'}</td>
                    <td>{formatDate(c.date_joined, lang)}</td>
                    <td>
                      {c.order_count > 0 ? (
                        <Link to={`/admin-portal/orders?search=${encodeURIComponent(c.phone || '')}`}>
                          {num(c.order_count)} <span className="muted">({t('admin.paidCount', '{{count}} پرداخت‌شده', { count: num(c.paid_order_count) })})</span>
                        </Link>
                      ) : '—'}
                    </td>
                    <td>{Number(c.total_spent) > 0 ? <Price amount={c.total_spent} /> : '—'}</td>
                    <td>{c.last_order_at ? formatDate(c.last_order_at, lang) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {data && <AdminPager page={page} pageSize={PAGE_SIZE} count={data.count} onChange={(p) => setFilter({ page: String(p) })} />}
    </div>
  );
}
