import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../../api/client';
import { ENDPOINTS } from '../../api/endpoints';
import Price from '../../components/Price';
import Icon from '../../components/Icon';
import Logo from '../../components/Logo';
import { formatDate } from '../../utils/persianDate';
import { paymentStatus, shippingMethodLabel } from '../../utils/orderStatus';
import { toPersianNumber } from '../../hooks/useLanguage';
import { usePageMeta } from '../../utils/seo';

// Printable invoice (A4/A5) plus a cut-off shipping label for the parcel.
export default function AdminInvoice() {
  const { orderNumber } = useParams();
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const [order, setOrder] = useState(null);
  const [shop, setShop] = useState({});
  const [failed, setFailed] = useState(false);

  usePageMeta({ title: `${t('admin.invoice', 'فاکتور')} ${orderNumber}`, noindex: true });

  useEffect(() => {
    apiClient.get(ENDPOINTS.adminOrderUpdate(orderNumber)).then((r) => setOrder(r.data)).catch(() => setFailed(true));
    apiClient.get(ENDPOINTS.shopInfo).then((r) => setShop(r.data)).catch(() => {});
  }, [orderNumber]);

  if (failed) return <div className="empty-panel"><h2>{t('admin.loadFailed', 'بارگذاری اطلاعات انجام نشد')}</h2></div>;
  if (!order) return <div className="loading"><div className="spinner" /></div>;

  const pay = paymentStatus(order.payment_status, lang);
  const storeName = lang === 'fa' ? 'فروشگاه هوپرزون' : 'HooperZone';

  return (
    <div className="admin-page invoice-page">
      <div className="invoice-toolbar hide-on-print">
        <Link to="/admin-portal/orders" className="btn btn-ghost btn-sm">
          <Icon name="arrowLeft" size={16} className="flip-ltr" /> {t('admin.orders', 'سفارش‌ها')}
        </Link>
        <button className="btn btn-primary" onClick={() => window.print()}>
          <Icon name="printer" size={18} /> {t('admin.printInvoiceNow', 'چاپ فاکتور')}
        </button>
      </div>

      <article className="invoice-sheet">
        <header className="invoice-head">
          <div className="invoice-brand">
            <Logo />
            <div className="invoice-store muted">
              {shop.store_address && <p>{shop.store_address}</p>}
              {shop.store_phone && <p dir="ltr">{num(shop.store_phone)}</p>}
              <p dir="ltr">hooperzone.ir</p>
            </div>
          </div>
          <div className="invoice-meta">
            <h1>{t('admin.invoiceTitle', 'فاکتور فروش')}</h1>
            <dl>
              <div><dt>{t('payment.orderNumber', 'شماره سفارش')}</dt><dd dir="ltr" className="mono">{order.order_number}</dd></div>
              <div><dt>{t('admin.date', 'تاریخ')}</dt><dd>{formatDate(order.created_at, lang)}</dd></div>
              <div><dt>{t('admin.payment', 'پرداخت')}</dt><dd>{pay.label}</dd></div>
              {order.payment_ref_id && <div><dt>{t('payment.refId', 'کد پیگیری پرداخت')}</dt><dd dir="ltr" className="mono">{order.payment_ref_id}</dd></div>}
            </dl>
          </div>
        </header>

        <section className="invoice-party">
          <h2>{t('admin.customer', 'مشتری')}</h2>
          <p><strong>{order.customer.name}</strong> · <span dir="ltr">{num(order.shipping_phone)}</span></p>
          <p>{[order.shipping_state, order.shipping_city].filter(Boolean).join('، ')} — {order.shipping_address}</p>
          <p>{t('checkout.zipCode')}: <span dir="ltr">{num(order.shipping_zip)}</span></p>
        </section>

        <table className="invoice-table">
          <thead>
            <tr>
              <th>#</th>
              <th>{t('admin.product', 'محصول')}</th>
              <th>{t('admin.unitPrice', 'قیمت واحد')}</th>
              <th>{t('product.quantity', 'تعداد')}</th>
              <th>{t('admin.lineTotal', 'جمع')}</th>
            </tr>
          </thead>
          <tbody>
            {order.items.map((item, i) => (
              <tr key={item.id}>
                <td>{num(i + 1)}</td>
                <td>{item.product_name}</td>
                <td><Price amount={item.product_price} /></td>
                <td>{num(item.quantity)}</td>
                <td><Price amount={item.subtotal} /></td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr><td colSpan={4}>{t('checkout.subtotal')}</td><td><Price amount={order.subtotal} /></td></tr>
            <tr>
              <td colSpan={4}>{t('checkout.shipping')} ({shippingMethodLabel(order.shipping_method, lang)})</td>
              <td><Price amount={order.shipping_cost} /></td>
            </tr>
            {Number(order.discount) > 0 && (
              <tr><td colSpan={4}>{t('admin.discount', 'تخفیف')}</td><td>−<Price amount={order.discount} /></td></tr>
            )}
            <tr className="invoice-total"><td colSpan={4}>{t('checkout.total')}</td><td><Price amount={order.total} /></td></tr>
          </tfoot>
        </table>

        {order.notes && <p className="invoice-notes">{t('checkout.orderNotes')}: {order.notes}</p>}
        <p className="invoice-thanks muted">{t('admin.invoiceThanks', 'از خرید شما سپاسگزاریم. برای پیگیری سفارش به بخش «سفارش‌های من» در سایت مراجعه کنید.')}</p>
      </article>

      <article className="shipping-label" aria-label={t('admin.shippingLabel', 'برچسب مرسوله')}>
        <div className="shipping-label-from">
          <span className="muted">{t('admin.sender', 'فرستنده')}</span>
          <strong>{storeName}</strong>
          {shop.store_address && <span>{shop.store_address}</span>}
          {shop.store_phone && <span dir="ltr">{num(shop.store_phone)}</span>}
        </div>
        <div className="shipping-label-to">
          <span className="muted">{t('admin.recipient', 'گیرنده')}</span>
          <strong>{order.customer.name}</strong>
          <span>{[order.shipping_state, order.shipping_city].filter(Boolean).join('، ')}</span>
          <span>{order.shipping_address}</span>
          <span>{t('checkout.zipCode')}: <b dir="ltr">{num(order.shipping_zip)}</b></span>
          <span>{t('checkout.phone')}: <b dir="ltr">{num(order.shipping_phone)}</b></span>
        </div>
        <div className="shipping-label-foot">
          <span>{shippingMethodLabel(order.shipping_method, lang)}</span>
          <span dir="ltr" className="mono">{order.order_number}</span>
        </div>
      </article>
    </div>
  );
}
