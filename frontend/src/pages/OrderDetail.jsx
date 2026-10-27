import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import { useToast } from '../context/ToastContext';
import { formatDate } from '../utils/persianDate';
import { toPersianNumber } from '../hooks/useLanguage';
import { ORDER_STEPS, orderStatus, paymentStatus, canPay, canCancel, shippingMethodLabel, trackingUrl } from '../utils/orderStatus';
import { GATEWAYS, startPayment } from '../utils/payment';
import { usePageMeta } from '../utils/seo';
import Price from '../components/Price';
import Icon from '../components/Icon';
import Breadcrumbs from '../components/Breadcrumbs';
import LoadingSpinner from '../components/LoadingSpinner';

export default function OrderDetail() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const { orderNumber } = useParams();
  const navigate = useNavigate();
  const { success, error: showError } = useToast();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [gateway, setGateway] = useState('zarinpal');
  const [busy, setBusy] = useState(false);

  usePageMeta({ title: t('orders.orderDetail'), noindex: true });

  useEffect(() => {
    apiClient
      .get(ENDPOINTS.orderDetail(orderNumber))
      .then((response) => setOrder(response.data))
      .catch(() => setOrder(null))
      .finally(() => setLoading(false));
  }, [orderNumber]);

  const handlePay = async () => {
    setBusy(true);
    try {
      await startPayment({ orderNumber, gateway, navigate });
    } catch (err) {
      showError(err.response?.data?.error || t('payment.startFailed', 'اتصال به درگاه پرداخت انجام نشد.'));
      setBusy(false);
    }
  };

  const handleCancel = async () => {
    if (!window.confirm(t('orders.cancelConfirm'))) return;
    setBusy(true);
    try {
      const { data } = await apiClient.post(ENDPOINTS.orderCancel(orderNumber));
      setOrder(data);
      success(t('orders.cancelled', 'سفارش لغو شد'));
    } catch (err) {
      showError(err.response?.data?.error || t('orders.cancelFailed'));
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  const crumbs = [
    { to: '/', label: t('common.home') },
    { to: '/orders', label: t('header.myOrders') },
    { label: order ? order.order_number : t('orders.notFound') },
  ];

  if (!order) {
    return (
      <div className="container">
        <Breadcrumbs items={crumbs} />
        <div className="empty-panel">
          <Icon name="box" size={44} strokeWidth={1.4} />
          <h2>{t('orders.notFound')}</h2>
          <Link to="/orders" className="btn btn-primary">{t('orders.viewAll')}</Link>
        </div>
      </div>
    );
  }

  const status = orderStatus(order.status, lang);
  const pay = paymentStatus(order.payment_status, lang);
  const currentStep = ORDER_STEPS.indexOf(order.status);

  return (
    <div className="order-page">
      <div className="container">
        <Breadcrumbs items={crumbs} />

        <header className="order-head">
          <div>
            <h1 className="display-title">
              {t('orders.orderTitle', 'سفارش')} <span dir="ltr">{order.order_number}</span>
            </h1>
            <p className="muted">{t('orders.placedOn', { date: formatDate(order.created_at, lang) })}</p>
          </div>
          <div className="order-badges">
            <span className={`status-pill tone-${status.tone}`}>{status.label}</span>
            <span className={`status-pill tone-${pay.tone}`}>{pay.label}</span>
          </div>
        </header>

        {canPay(order) && (
          <section className="pay-banner">
            <div>
              <h2>{t('payment.payNowTitle', 'پرداخت سفارش')}</h2>
              <p>{t('payment.payNowText', 'سفارش شما ثبت شده و پس از پرداخت، آماده‌سازی و ارسال می‌شود.')}</p>
            </div>
            <div className="pay-banner-actions">
              <div className="gateway-chips" role="radiogroup" aria-label={t('checkout.paymentMethod', 'روش پرداخت')}>
                {GATEWAYS.map((g) => (
                  <button
                    key={g.key}
                    type="button"
                    role="radio"
                    aria-checked={gateway === g.key}
                    className={`chip ${gateway === g.key ? 'active' : ''}`}
                    onClick={() => setGateway(g.key)}
                  >
                    {lang === 'fa' ? g.fa : g.en}
                  </button>
                ))}
              </div>
              <button className="btn btn-secondary btn-lg" onClick={handlePay} disabled={busy}>
                <Icon name="card" size={20} /> {t('payment.payAmount', 'پرداخت')} <Price amount={order.total} />
              </button>
            </div>
          </section>
        )}

        {order.status !== 'cancelled' && (
          <ol className="order-timeline" aria-label={t('orders.progress', 'وضعیت سفارش')}>
            {ORDER_STEPS.map((step, i) => (
              <li key={step} className={i < currentStep ? 'done' : i === currentStep ? 'current' : ''}>
                <span className="step-dot">{i < currentStep ? <Icon name="check" size={14} strokeWidth={2.4} /> : num(i + 1)}</span>
                <span>{step === 'pending' ? t('orders.stepPlaced', 'ثبت سفارش') : orderStatus(step, lang).label}</span>
              </li>
            ))}
          </ol>
        )}

        <div className="cart-layout">
          <div>
            <section className="form-card">
              <h2><Icon name="box" size={20} /> {t('orders.items')}</h2>
              <ul className="order-lines">
                {order.items.map((item) => (
                  <li key={item.id}>
                    <span className="order-line-name">{item.product_name}</span>
                    <span className="muted">× {num(item.quantity)}</span>
                    <Price amount={item.subtotal} />
                  </li>
                ))}
              </ul>
            </section>

            <section className="form-card">
              <h2><Icon name="truck" size={20} /> {t('orders.shippingAddress')}</h2>
              <address className="order-address">
                <p>{order.shipping_address}</p>
                <p>{[order.shipping_state, order.shipping_city].filter(Boolean).join('، ')}</p>
                <p>{t('checkout.zipCode')}: <span dir="ltr">{num(order.shipping_zip)}</span></p>
                <p>{t('checkout.phone')}: <span dir="ltr">{num(order.shipping_phone)}</span></p>
              </address>
              {order.notes && <p className="muted">{t('checkout.orderNotes')}: {order.notes}</p>}
              <div className="shipment-box">
                <div>
                  <span className="muted">{t('checkout.shippingMethod', 'روش ارسال')}</span>
                  <strong>{shippingMethodLabel(order.shipping_method, lang)}</strong>
                </div>
                {order.tracking_code ? (
                  <div>
                    <span className="muted">{t('orders.trackingCode', 'کد رهگیری مرسوله')}</span>
                    <strong dir="ltr" className="mono">{order.tracking_code}</strong>
                    <a href={trackingUrl(order.shipping_method)} target="_blank" rel="noreferrer" className="link-arrow">
                      {t('orders.trackParcel', 'پیگیری مرسوله')} <Icon name="arrowLeft" size={16} className="flip-ltr" />
                    </a>
                  </div>
                ) : (
                  order.payment_status === 'paid' && order.status !== 'cancelled' && (
                    <p className="muted">{t('orders.trackingSoon', 'کد رهگیری پس از ارسال مرسوله همین‌جا نمایش داده می‌شود.')}</p>
                  )
                )}
                {order.payment_ref_id && (
                  <div>
                    <span className="muted">{t('payment.refId', 'کد پیگیری پرداخت')}</span>
                    <strong dir="ltr" className="mono">{order.payment_ref_id}</strong>
                  </div>
                )}
              </div>
            </section>
          </div>

          <aside className="summary-card">
            <h2>{t('cart.orderSummary')}</h2>
            <dl className="summary-rows">
              <div><dt>{t('cart.subtotal')}</dt><dd><Price amount={order.subtotal} /></dd></div>
              <div>
                <dt>{t('cart.shipping')} <span className="muted">({shippingMethodLabel(order.shipping_method, lang)})</span></dt>
                <dd><Price amount={order.shipping_cost} /></dd>
              </div>
              <div className="summary-total"><dt>{t('cart.total')}</dt><dd><Price amount={order.total} /></dd></div>
            </dl>
            {canCancel(order) && order.payment_status !== 'paid' && (
              <button onClick={handleCancel} className="btn btn-outline btn-full" disabled={busy}>
                {t('orders.cancelOrder')}
              </button>
            )}
            <Link to="/orders" className="link-arrow summary-back">
              <Icon name="chevronRight" size={16} className="flip-ltr" /> {t('orders.backToOrders')}
            </Link>
          </aside>
        </div>
      </div>
    </div>
  );
}
