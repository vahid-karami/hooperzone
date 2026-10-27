import { Fragment, useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../../api/client';
import { ENDPOINTS } from '../../api/endpoints';
import { useToast } from '../../context/ToastContext';
import Price from '../../components/Price';
import Icon from '../../components/Icon';
import AdminPager from '../../components/admin/AdminPager';
import { formatDate } from '../../utils/persianDate';
import { ORDER_STEPS, orderStatus, paymentStatus, shippingMethodLabel, SHIPPING_METHODS } from '../../utils/orderStatus';
import { downloadFile } from '../../utils/download';
import { toEnglishDigits } from '../../utils/digits';
import { toPersianNumber } from '../../hooks/useLanguage';
import { usePageMeta } from '../../utils/seo';

const STATUS_OPTIONS = [...ORDER_STEPS, 'cancelled'];
const PAGE_SIZE = 25;
const FILTER_KEYS = ['status', 'payment_status', 'shipping_method', 'search', 'date_from', 'date_to'];

// Statuses staff may pick for an order: the current one, the ones after it, and cancel.
const nextStatuses = (current) => {
  if (current === 'cancelled') return ['cancelled'];
  const idx = ORDER_STEPS.indexOf(current);
  const forward = ORDER_STEPS.slice(Math.max(idx, 0));
  return current === 'delivered' ? forward : [...forward, 'cancelled'];
};

function TrackingEditor({ order, onSaved }) {
  const { t } = useTranslation();
  const { success, error: showError } = useToast();
  const [code, setCode] = useState(order.tracking_code || '');
  const [saving, setSaving] = useState(false);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = { tracking_code: toEnglishDigits(code.trim()) };
      // Saving a tracking code on a paid, not-yet-shipped order also marks it shipped.
      if (payload.tracking_code && ['confirmed', 'processing'].includes(order.status)) payload.status = 'shipped';
      const { data } = await apiClient.patch(ENDPOINTS.adminOrderUpdate(order.order_number), payload);
      onSaved(data);
      success(t('admin.trackingSaved', 'کد رهگیری ذخیره شد'));
    } catch (err) {
      showError(err.response?.data?.error || t('admin.updateFailed', 'به‌روزرسانی انجام نشد'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="tracking-form" onSubmit={save}>
      <label className="form-label" htmlFor={`trk-${order.id}`}>{t('admin.trackingCode', 'کد رهگیری مرسوله')}</label>
      <div className="tracking-row">
        <input
          id={`trk-${order.id}`}
          className="form-input"
          dir="ltr"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder={t('admin.trackingPlaceholder', 'مثلاً ۲۴ رقم پست')}
        />
        <button type="submit" className="btn btn-primary btn-sm" disabled={saving || code === (order.tracking_code || '')}>
          {saving ? t('common.loading') : t('admin.save', 'ذخیره')}
        </button>
      </div>
      {['confirmed', 'processing'].includes(order.status) && (
        <p className="field-hint">{t('admin.trackingHint', 'با ذخیره کد، وضعیت سفارش «ارسال شده» می‌شود.')}</p>
      )}
    </form>
  );
}

export default function AdminOrders() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const { success, error: showError } = useToast();
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState(null);
  const [expanded, setExpanded] = useState(null);
  const [selected, setSelected] = useState(() => new Set());
  const [bulkStatus, setBulkStatus] = useState('processing');
  const [search, setSearch] = useState(params.get('search') || '');
  const [showFilters, setShowFilters] = useState(Boolean(params.get('date_from') || params.get('date_to') || params.get('shipping_method')));

  const filters = Object.fromEntries(FILTER_KEYS.map((k) => [k, params.get(k) || '']));
  const page = Number(params.get('page')) || 1;
  const filterKey = FILTER_KEYS.map((k) => filters[k]).join('|');

  usePageMeta({ title: t('admin.orders', 'سفارش‌ها'), noindex: true });

  const queryParams = useCallback(
    () => Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [filterKey],
  );

  const load = useCallback(() => {
    let active = true;
    apiClient
      .get(ENDPOINTS.adminOrders, { params: { ...queryParams(), page, page_size: PAGE_SIZE } })
      .then((res) => active && setData(res.data))
      .catch(() => active && setData({ count: 0, results: [] }));
    return () => {
      active = false;
    };
  }, [queryParams, page]);

  useEffect(() => {
    setData(null);
    setSelected(new Set());
    return load();
  }, [load]);

  const setFilter = (changes) => {
    const next = new URLSearchParams(params);
    Object.entries(changes).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)));
    if (!('page' in changes)) next.delete('page');
    setParams(next);
  };

  const replaceOrder = (updated) =>
    setData((d) => ({ ...d, results: d.results.map((o) => (o.id === updated.id ? updated : o)) }));

  const changeStatus = async (order, status) => {
    if (status === order.status) return;
    if (status === 'cancelled' && !window.confirm(t('admin.cancelConfirm', 'سفارش لغو و کالاها به موجودی برگردانده شوند؟'))) return;
    try {
      const res = await apiClient.patch(ENDPOINTS.adminOrderUpdate(order.order_number), { status });
      replaceOrder(res.data);
      success(t('admin.statusUpdated', 'وضعیت سفارش به‌روز شد'));
    } catch (err) {
      showError(err.response?.data?.error || t('admin.updateFailed', 'به‌روزرسانی انجام نشد'));
    }
  };

  const applyBulk = async () => {
    const numbers = [...selected];
    if (bulkStatus === 'cancelled' && !window.confirm(t('admin.cancelConfirm', 'سفارش لغو و کالاها به موجودی برگردانده شوند؟'))) return;
    try {
      const res = await apiClient.post(ENDPOINTS.adminOrderBulkStatus, { order_numbers: numbers, status: bulkStatus });
      const { updated, skipped } = res.data;
      if (updated.length) success(t('admin.bulkUpdated', '{{count}} سفارش به‌روز شد', { count: num(updated.length) }));
      if (skipped.length) showError(t('admin.bulkSkipped', '{{count}} سفارش قابل تغییر نبود', { count: num(skipped.length) }));
      setSelected(new Set());
      load();
    } catch (err) {
      showError(err.response?.data?.error || t('admin.updateFailed', 'به‌روزرسانی انجام نشد'));
    }
  };

  const exportCsv = () =>
    downloadFile(ENDPOINTS.adminOrderExport, queryParams(), 'orders.csv').catch(() =>
      showError(t('admin.exportFailed', 'دریافت فایل انجام نشد')),
    );

  const orders = data?.results;
  const allSelected = orders?.length > 0 && orders.every((o) => selected.has(o.order_number));
  const toggleAll = () => setSelected(allSelected ? new Set() : new Set(orders.map((o) => o.order_number)));
  const toggleOne = (number) =>
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(number)) next.delete(number);
      else next.add(number);
      return next;
    });

  const tabs = [
    { key: '', label: t('orders.all', 'همه') },
    ...STATUS_OPTIONS.map((s) => ({ key: s, label: orderStatus(s, lang).label })),
  ];

  return (
    <div className="admin-page">
      <header className="admin-page-head">
        <div>
          <h1>{t('admin.orders', 'سفارش‌ها')}</h1>
          <p className="muted">
            {data ? t('admin.ordersFound', '{{count}} سفارش', { count: num(data.count) }) : t('admin.ordersHint', 'پیگیری، تغییر وضعیت و ارسال سفارش‌ها')}
          </p>
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
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={t('admin.searchOrders', 'شماره سفارش، نام یا موبایل مشتری')}
              aria-label={t('common.search')}
            />
          </form>
          <button type="button" className={`btn btn-outline ${showFilters ? 'is-on' : ''}`} onClick={() => setShowFilters((v) => !v)} aria-expanded={showFilters}>
            <Icon name="filter" size={18} /> {t('admin.filters', 'فیلترها')}
          </button>
          <button type="button" className="btn btn-outline" onClick={exportCsv}>
            <Icon name="download" size={18} /> {t('admin.exportCsv', 'خروجی اکسل')}
          </button>
        </div>
      </header>

      {showFilters && (
        <div className="admin-filter-bar">
          <label className="form-group">
            <span className="form-label">{t('admin.dateFrom', 'از تاریخ')}</span>
            <input type="date" className="form-input" value={filters.date_from} onChange={(e) => setFilter({ date_from: e.target.value })} />
          </label>
          <label className="form-group">
            <span className="form-label">{t('admin.dateTo', 'تا تاریخ')}</span>
            <input type="date" className="form-input" value={filters.date_to} onChange={(e) => setFilter({ date_to: e.target.value })} />
          </label>
          <label className="form-group">
            <span className="form-label">{t('checkout.shippingMethod', 'روش ارسال')}</span>
            <select className="form-select" value={filters.shipping_method} onChange={(e) => setFilter({ shipping_method: e.target.value })}>
              <option value="">{t('orders.all', 'همه')}</option>
              {SHIPPING_METHODS.map((m) => <option key={m} value={m}>{shippingMethodLabel(m, lang)}</option>)}
            </select>
          </label>
          <label className="form-group">
            <span className="form-label">{t('admin.payment', 'پرداخت')}</span>
            <select className="form-select" value={filters.payment_status} onChange={(e) => setFilter({ payment_status: e.target.value })}>
              <option value="">{t('orders.all', 'همه')}</option>
              {['paid', 'pending', 'failed', 'refunded'].map((p) => <option key={p} value={p}>{paymentStatus(p, lang).label}</option>)}
            </select>
          </label>
          <button
            type="button"
            className="text-btn"
            onClick={() => {
              setSearch('');
              setFilter(Object.fromEntries(FILTER_KEYS.map((k) => [k, ''])));
            }}
          >
            {t('admin.clearFilters', 'پاک کردن فیلترها')}
          </button>
        </div>
      )}

      <div className="tab-row" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.key || 'all'}
            role="tab"
            aria-selected={filters.status === tab.key}
            className={`tab ${filters.status === tab.key ? 'active' : ''}`}
            onClick={() => setFilter({ status: tab.key })}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {selected.size > 0 && (
        <div className="bulk-bar" role="region" aria-label={t('admin.bulkActions', 'عملیات گروهی')}>
          <strong>{t('admin.selectedCount', '{{count}} مورد انتخاب شده', { count: num(selected.size) })}</strong>
          <select className="form-select" value={bulkStatus} onChange={(e) => setBulkStatus(e.target.value)} aria-label={t('admin.status', 'وضعیت')}>
            {STATUS_OPTIONS.filter((s) => s !== 'pending').map((s) => (
              <option key={s} value={s}>{orderStatus(s, lang).label}</option>
            ))}
          </select>
          <button className="btn btn-primary btn-sm" onClick={applyBulk}>{t('admin.apply', 'اعمال')}</button>
          <button className="text-btn" onClick={() => setSelected(new Set())}>{t('admin.cancel', 'انصراف')}</button>
        </div>
      )}

      <section className="admin-card flush">
        {data === null ? (
          <div className="loading"><div className="spinner" /></div>
        ) : orders.length === 0 ? (
          <p className="muted empty-inline">{t('admin.noMatchingOrders', 'سفارشی با این فیلتر پیدا نشد.')}</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th className="check-col">
                    <input type="checkbox" checked={allSelected} onChange={toggleAll} aria-label={t('admin.selectAll', 'انتخاب همه')} />
                  </th>
                  <th aria-label={t('orders.details', 'جزئیات سفارش')} />
                  <th>{t('payment.orderNumber', 'شماره سفارش')}</th>
                  <th>{t('admin.customer', 'مشتری')}</th>
                  <th>{t('admin.date', 'تاریخ')}</th>
                  <th>{t('cart.total')}</th>
                  <th>{t('checkout.shippingMethod', 'روش ارسال')}</th>
                  <th>{t('admin.payment', 'پرداخت')}</th>
                  <th>{t('admin.status', 'وضعیت')}</th>
                </tr>
              </thead>
              <tbody>
                {orders.map((o) => {
                  const pay = paymentStatus(o.payment_status, lang);
                  const open = expanded === o.id;
                  return (
                    <Fragment key={o.id}>
                      <tr className={`${open ? 'is-open' : ''} ${selected.has(o.order_number) ? 'is-selected' : ''}`}>
                        <td className="check-col">
                          <input
                            type="checkbox"
                            checked={selected.has(o.order_number)}
                            onChange={() => toggleOne(o.order_number)}
                            aria-label={o.order_number}
                          />
                        </td>
                        <td>
                          <button
                            className="icon-btn row-toggle"
                            onClick={() => setExpanded(open ? null : o.id)}
                            aria-expanded={open}
                            aria-label={t('orders.details', 'جزئیات سفارش')}
                          >
                            <Icon name="chevronDown" size={18} />
                          </button>
                        </td>
                        <td dir="ltr" className="mono">{o.order_number}</td>
                        <td>
                          <div className="cell-stack">
                            <strong>{o.customer.name}</strong>
                            <span dir="ltr">{num(o.customer.phone || o.shipping_phone)}</span>
                          </div>
                        </td>
                        <td>{formatDate(o.created_at, lang)}</td>
                        <td><Price amount={o.total} /></td>
                        <td>
                          <div className="cell-stack">
                            <span>{shippingMethodLabel(o.shipping_method, lang)}</span>
                            {o.tracking_code && <span className="muted mono" dir="ltr">{o.tracking_code}</span>}
                          </div>
                        </td>
                        <td><span className={`status-pill tone-${pay.tone}`}>{pay.label}</span></td>
                        <td>
                          <select
                            className={`status-select tone-${orderStatus(o.status, lang).tone}`}
                            value={o.status}
                            onChange={(e) => changeStatus(o, e.target.value)}
                            disabled={o.status === 'cancelled'}
                            aria-label={t('admin.status', 'وضعیت')}
                          >
                            {nextStatuses(o.status).map((s) => (
                              <option key={s} value={s}>{orderStatus(s, lang).label}</option>
                            ))}
                          </select>
                        </td>
                      </tr>
                      {open && (
                        <tr className="row-detail">
                          <td colSpan={9}>
                            <div className="row-detail-grid three">
                              <div>
                                <h3>{t('orders.items')}</h3>
                                <ul className="order-lines">
                                  {o.items.map((item) => (
                                    <li key={item.id}>
                                      <span className="order-line-name">{item.product_name}</span>
                                      <span className="muted">× {num(item.quantity)}</span>
                                      <Price amount={item.subtotal} />
                                    </li>
                                  ))}
                                  <li className="order-line-sum">
                                    <span className="order-line-name">{t('checkout.shipping')}</span>
                                    <span />
                                    <Price amount={o.shipping_cost} />
                                  </li>
                                </ul>
                              </div>
                              <div>
                                <h3>{t('orders.shippingAddress')}</h3>
                                <address className="order-address">
                                  <p>{o.shipping_address}</p>
                                  <p>{[o.shipping_state, o.shipping_city].filter(Boolean).join('، ')}</p>
                                  <p>{t('checkout.zipCode')}: <span dir="ltr">{num(o.shipping_zip)}</span></p>
                                  <p>{t('checkout.phone')}: <span dir="ltr">{num(o.shipping_phone)}</span></p>
                                </address>
                                {o.notes && <p className="muted">{t('checkout.orderNotes')}: {o.notes}</p>}
                                {o.payment_ref_id && (
                                  <p className="muted">{t('payment.refId', 'کد پیگیری پرداخت')}: <span dir="ltr" className="mono">{o.payment_ref_id}</span></p>
                                )}
                              </div>
                              <div className="row-detail-actions">
                                {o.status !== 'cancelled' && <TrackingEditor order={o} onSaved={replaceOrder} />}
                                <Link to={`/admin-portal/orders/${o.order_number}/invoice`} className="btn btn-outline btn-sm">
                                  <Icon name="printer" size={16} /> {t('admin.printInvoice', 'چاپ فاکتور و برچسب')}
                                </Link>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {data && <AdminPager page={page} pageSize={PAGE_SIZE} count={data.count} onChange={(p) => setFilter({ page: String(p) })} />}
    </div>
  );
}
