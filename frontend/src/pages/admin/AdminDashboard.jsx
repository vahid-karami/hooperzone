import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../../api/client';
import { ENDPOINTS } from '../../api/endpoints';
import Price from '../../components/Price';
import Icon from '../../components/Icon';
import { Skeleton } from '../../components/Skeletons';
import { formatDate } from '../../utils/persianDate';
import { orderStatus, paymentStatus } from '../../utils/orderStatus';
import { toPersianNumber } from '../../hooks/useLanguage';
import { usePageMeta } from '../../utils/seo';

function RevenueChart({ days, lang, title }) {
  const { t } = useTranslation();
  const max = Math.max(...days.map((d) => Number(d.revenue)), 1);
  const short = days.length <= 7;
  const dayLabel = (iso) =>
    new Intl.DateTimeFormat(lang === 'fa' ? 'fa-IR' : 'en-US', short ? { weekday: 'short' } : { day: 'numeric' }).format(new Date(`${iso}T12:00:00`));
  const money = (v) => `${Number(v).toLocaleString(lang === 'fa' ? 'fa-IR' : 'en-US')} ${t('common.toman', 'تومان')}`;

  return (
    <figure className="chart">
      <figcaption className="chart-title">{title}</figcaption>
      <div className={`chart-bars ${short ? '' : 'dense'}`} role="img" aria-label={title}>
        {days.map((d) => {
          const h = (Number(d.revenue) / max) * 100;
          return (
            <div key={d.date} className="chart-col" tabIndex={0} aria-label={`${dayLabel(d.date)}: ${money(d.revenue)}`}>
              <span className="chart-tip" role="tooltip">
                <strong>{money(d.revenue)}</strong>
                <span>{t('admin.ordersCount', '{{count}} سفارش', { count: lang === 'fa' ? toPersianNumber(d.orders) : d.orders })}</span>
              </span>
              <span className="chart-bar" style={{ height: `${Math.max(h, Number(d.revenue) > 0 ? 3 : 0)}%` }} />
              <span className="chart-label">{dayLabel(d.date)}</span>
            </div>
          );
        })}
      </div>
      <table className="sr-only">
        <caption>{title}</caption>
        <tbody>
          {days.map((d) => (
            <tr key={d.date}><th scope="row">{dayLabel(d.date)}</th><td>{money(d.revenue)}</td></tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}

export default function AdminDashboard() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const [stats, setStats] = useState(null);
  const [failed, setFailed] = useState(false);
  const [range, setRange] = useState(7);

  usePageMeta({ title: t('admin.dashboard', 'داشبورد'), noindex: true });

  useEffect(() => {
    apiClient
      .get(ENDPOINTS.adminStats, { params: { days: range } })
      .then((res) => setStats(res.data))
      .catch(() => setFailed(true));
  }, [range]);

  const ranges = [
    { days: 7, label: t('admin.range7', '۷ روز') },
    { days: 30, label: t('admin.range30', '۳۰ روز') },
    { days: 90, label: t('admin.range90', '۹۰ روز') },
  ];

  if (failed) {
    return <div className="empty-panel"><h2>{t('admin.loadFailed', 'بارگذاری اطلاعات انجام نشد')}</h2></div>;
  }

  const tiles = stats && [
    { icon: 'card', label: t('admin.revenueTotal', 'کل فروش'), value: <Price amount={stats.revenue_total} />, sub: <>{t('admin.last30', '۳۰ روز اخیر:')} <Price amount={stats.revenue_30d} /></> },
    { icon: 'box', label: t('admin.ordersTotal', 'کل سفارش‌ها'), value: num(stats.orders_total), sub: t('admin.today', 'امروز: {{count}}', { count: num(stats.orders_today) }) },
    { icon: 'truck', label: t('admin.toShip', 'آماده ارسال'), value: num(stats.to_ship), sub: t('admin.toShipHint', 'پرداخت‌شده، ارسال‌نشده'), to: '/admin-portal/orders?status=confirmed', tone: stats.to_ship ? 'accent' : '' },
    { icon: 'returns', label: t('admin.awaitingPayment', 'در انتظار پرداخت'), value: num(stats.awaiting_payment), sub: t('admin.customers', '{{count}} مشتری', { count: num(stats.customers) }), to: '/admin-portal/orders?payment_status=pending' },
  ];

  return (
    <div className="admin-page">
      <header className="admin-page-head">
        <div>
          <h1>{t('admin.dashboard', 'داشبورد')}</h1>
          <p className="muted">{t('admin.dashboardHint', 'نمای کلی فروشگاه در یک نگاه')}</p>
        </div>
        <div className="segmented" role="group" aria-label={t('admin.range', 'بازه زمانی')}>
          {ranges.map((r) => (
            <button key={r.days} className={range === r.days ? 'active' : ''} aria-pressed={range === r.days} onClick={() => setRange(r.days)}>
              {r.label}
            </button>
          ))}
        </div>
      </header>

      <div className="stat-grid">
        {stats
          ? tiles.map((tile) => {
              const body = (
                <>
                  <span className="stat-icon"><Icon name={tile.icon} size={22} /></span>
                  <span className="stat-label">{tile.label}</span>
                  <strong className="stat-value">{tile.value}</strong>
                  <span className="stat-sub">{tile.sub}</span>
                </>
              );
              return tile.to ? (
                <Link key={tile.label} to={tile.to} className={`stat-tile ${tile.tone || ''}`}>{body}</Link>
              ) : (
                <div key={tile.label} className="stat-tile">{body}</div>
              );
            })
          : [1, 2, 3, 4].map((i) => <Skeleton key={i} className="stat-tile" style={{ height: 132 }} />)}
      </div>

      <div className="admin-grid">
        <section className="admin-card">
          {stats ? (
            <>
              <RevenueChart
                days={stats.last_7_days}
                lang={lang}
                title={t('admin.revenueRange', 'فروش پرداخت‌شده در {{days}} روز اخیر', { days: num(stats.range_days) })}
              />
              <dl className="range-summary">
                <div><dt>{t('admin.revenue', 'فروش')}</dt><dd><Price amount={stats.revenue_range} /></dd></div>
                <div><dt>{t('admin.paidOrders', 'سفارش پرداخت‌شده')}</dt><dd>{num(stats.orders_range)}</dd></div>
                <div><dt>{t('admin.aov', 'میانگین هر سفارش')}</dt><dd><Price amount={stats.average_order_value} /></dd></div>
              </dl>
            </>
          ) : <Skeleton style={{ height: 240 }} />}
        </section>

        <section className="admin-card">
          <div className="admin-card-head">
            <h2>{t('admin.bestSellers', 'پرفروش‌ترین‌ها')}</h2>
          </div>
          {stats && stats.best_sellers.length === 0 && <p className="muted">{t('admin.noSales', 'در این بازه فروشی ثبت نشده است.')}</p>}
          <ol className="best-sellers">
            {stats?.best_sellers.map((p) => (
              <li key={p.slug || p.name}>
                {p.slug ? <Link to={`/products/${p.slug}`}>{p.name}</Link> : <span>{p.name}</span>}
                <span className="muted">{t('admin.soldCount', '{{count}} فروش', { count: num(p.quantity) })}</span>
                <Price amount={p.revenue} />
              </li>
            ))}
          </ol>

          <div className="admin-card-head spaced">
            <h2>{t('admin.lowStock', 'موجودی رو به اتمام')}</h2>
            <Link to="/admin-portal/products" className="link-arrow">{t('common.viewAll')} <Icon name="arrowLeft" size={16} /></Link>
          </div>
          {stats && stats.low_stock.length === 0 && <p className="muted">{t('admin.stockOk', 'موجودی همه محصولات کافی است.')}</p>}
          <ul className="low-stock">
            {stats?.low_stock.map((p) => (
              <li key={p.id}>
                <Link to={`/products/${p.slug}`}>{p.name}</Link>
                <span className={`status-pill ${p.stock === 0 ? 'tone-bad' : 'tone-warn'}`}>
                  {p.stock === 0 ? t('common.outOfStock') : t('admin.left', '{{count}} عدد', { count: num(p.stock) })}
                </span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="admin-card">
        <div className="admin-card-head">
          <h2>{t('admin.recentOrders', 'آخرین سفارش‌ها')}</h2>
          <Link to="/admin-portal/orders" className="link-arrow">{t('common.viewAll')} <Icon name="arrowLeft" size={16} /></Link>
        </div>
        {stats?.recent_orders.length === 0 ? (
          <p className="muted">{t('admin.noOrders', 'هنوز سفارشی ثبت نشده است.')}</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('payment.orderNumber', 'شماره سفارش')}</th>
                  <th>{t('admin.customer', 'مشتری')}</th>
                  <th>{t('admin.date', 'تاریخ')}</th>
                  <th>{t('cart.total')}</th>
                  <th>{t('admin.status', 'وضعیت')}</th>
                </tr>
              </thead>
              <tbody>
                {stats?.recent_orders.map((o) => {
                  const st = orderStatus(o.status, lang);
                  const pay = paymentStatus(o.payment_status, lang);
                  return (
                    <tr key={o.id}>
                      <td><Link to={`/admin-portal/orders?search=${o.order_number}`} dir="ltr">{o.order_number}</Link></td>
                      <td>{o.customer.name}</td>
                      <td>{formatDate(o.created_at, lang)}</td>
                      <td><Price amount={o.total} /></td>
                      <td>
                        <span className={`status-pill tone-${st.tone}`}>{st.label}</span>{' '}
                        <span className={`status-pill tone-${pay.tone}`}>{pay.label}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
