import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import { useToast } from '../context/ToastContext';
import AccountLayout from '../components/AccountLayout';
import Icon from '../components/Icon';
import Price from '../components/Price';
import { Skeleton } from '../components/Skeletons';
import { formatDate } from '../utils/persianDate';
import { orderStatus, paymentStatus, canPay } from '../utils/orderStatus';
import { startPayment } from '../utils/payment';
import { toPersianNumber } from '../hooks/useLanguage';
import { usePageMeta } from '../utils/seo';

const FILTERS = [
  { key: 'all', fa: 'همه', en: 'All', test: () => true },
  { key: 'unpaid', fa: 'در انتظار پرداخت', en: 'Awaiting payment', test: (o) => canPay(o) },
  { key: 'active', fa: 'در جریان', en: 'In progress', test: (o) => o.payment_status === 'paid' && ['confirmed', 'processing', 'shipped'].includes(o.status) },
  { key: 'delivered', fa: 'تحویل شده', en: 'Delivered', test: (o) => o.status === 'delivered' },
  { key: 'cancelled', fa: 'لغو شده', en: 'Cancelled', test: (o) => o.status === 'cancelled' },
];

export default function Orders() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const navigate = useNavigate();
  const { error: showError } = useToast();
  const [orders, setOrders] = useState(null);
  const [filter, setFilter] = useState('all');
  const [paying, setPaying] = useState(null);

  usePageMeta({ title: t('header.myOrders'), noindex: true });

  useEffect(() => {
    apiClient
      .get(ENDPOINTS.orders)
      .then((res) => setOrders(res.data))
      .catch(() => setOrders([]));
  }, []);

  const handlePay = async (orderNumber) => {
    setPaying(orderNumber);
    try {
      await startPayment({ orderNumber, gateway: 'zarinpal', navigate });
    } catch (err) {
      showError(err.response?.data?.error || t('payment.startFailed'));
      setPaying(null);
    }
  };

  const counts = Object.fromEntries(FILTERS.map((f) => [f.key, (orders || []).filter(f.test).length]));
  const visible = (orders || []).filter(FILTERS.find((f) => f.key === filter).test);

  return (
    <AccountLayout title={t('header.myOrders')}>
      {orders === null ? (
        <div className="order-list" aria-hidden="true">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="order-row" style={{ height: 150 }} />)}
        </div>
      ) : orders.length === 0 ? (
        <div className="empty-panel">
          <Icon name="box" size={44} strokeWidth={1.4} />
          <h2>{t('orders.noOrders')}</h2>
          <p>{t('orders.noOrdersDesc')}</p>
          <Link to="/products" className="btn btn-primary">{t('cart.browseProducts')}</Link>
        </div>
      ) : (
        <>
          <div className="tab-row" role="tablist" aria-label={t('orders.filter', 'فیلتر سفارش‌ها')}>
            {FILTERS.map((f) => (
              <button
                key={f.key}
                role="tab"
                aria-selected={filter === f.key}
                className={`tab ${filter === f.key ? 'active' : ''}`}
                onClick={() => setFilter(f.key)}
              >
                {lang === 'fa' ? f.fa : f.en}
                <span className="tab-count">{num(counts[f.key])}</span>
              </button>
            ))}
          </div>

          {visible.length === 0 ? (
            <p className="muted empty-inline">{t('orders.noneInFilter', 'سفارشی در این دسته نیست.')}</p>
          ) : (
            <ul className="order-list">
              {visible.map((order) => {
                const status = orderStatus(order.status, lang);
                const pay = paymentStatus(order.payment_status, lang);
                const itemCount = order.items.reduce((n, i) => n + i.quantity, 0);
                return (
                  <li key={order.id} className="order-row">
                    <div className="order-row-head">
                      <div>
                        <Link to={`/orders/${order.order_number}`} className="order-row-number" dir="ltr">{order.order_number}</Link>
                        <span className="muted">{formatDate(order.created_at, lang)}</span>
                      </div>
                      <div className="order-badges">
                        <span className={`status-pill tone-${status.tone}`}>{status.label}</span>
                        {order.status !== 'cancelled' && <span className={`status-pill tone-${pay.tone}`}>{pay.label}</span>}
                      </div>
                    </div>

                    <div className="order-row-items">
                      {order.items.slice(0, 4).map((item) => (
                        <span key={item.id} className="order-thumb" title={item.product_name}>
                          {item.product_image ? <img src={item.product_image} alt={item.product_name} /> : <Icon name="box" size={22} />}
                          {item.quantity > 1 && <span className="summary-qty">{num(item.quantity)}</span>}
                        </span>
                      ))}
                      {order.items.length > 4 && <span className="order-thumb more">+{num(order.items.length - 4)}</span>}
                      <span className="order-row-summary">
                        {order.items.map((i) => i.product_name).slice(0, 2).join('، ')}
                        {order.items.length > 2 ? ' …' : ''}
                      </span>
                    </div>

                    <div className="order-row-foot">
                      <span>
                        {t('orders.itemsCount', '{{count}} کالا', { count: num(itemCount) })} · <strong><Price amount={order.total} /></strong>
                      </span>
                      <div className="order-row-actions">
                        {canPay(order) && (
                          <button className="btn btn-primary btn-sm" onClick={() => handlePay(order.order_number)} disabled={paying === order.order_number}>
                            <Icon name="card" size={16} /> {t('payment.payAmount', 'پرداخت')}
                          </button>
                        )}
                        <Link to={`/orders/${order.order_number}`} className="btn btn-outline btn-sm">
                          {t('orders.details', 'جزئیات سفارش')}
                        </Link>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </>
      )}
    </AccountLayout>
  );
}
