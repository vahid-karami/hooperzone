import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import Icon from '../components/Icon';
import Price from '../components/Price';
import { usePageMeta } from '../utils/seo';

// Landing page the payment gateway redirects back to.
export default function PaymentResult() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const [state, setState] = useState({ status: 'verifying' });
  const started = useRef(false);

  const orderNumber = params.get('order_number');
  const gateway = params.get('gateway') || 'zarinpal';
  const authority = params.get('Authority') || params.get('authority') || params.get('id');

  usePageMeta({ title: t('payment.resultTitle', 'نتیجه پرداخت'), noindex: true });

  useEffect(() => {
    // Verify exactly once (StrictMode mounts effects twice in development).
    if (started.current) return;
    started.current = true;

    if (!orderNumber || !authority) {
      setState({ status: 'failed', error: t('payment.missingInfo', 'اطلاعات پرداخت ناقص است.') });
      return;
    }
    apiClient
      .post(ENDPOINTS.paymentVerify, { order_number: orderNumber, authority, gateway })
      .then(({ data }) => setState({ status: 'paid', refId: data.ref_id, order: data.order }))
      .catch((err) =>
        setState({
          status: 'failed',
          error: err.response?.data?.error || t('payment.verifyFailed', 'پرداخت تأیید نشد.'),
        }),
      );
  }, [orderNumber, authority, gateway, t]);


  return (
    <div className="container">
      <div className={`result-panel ${state.status}`} role="status" aria-live="polite">
        {state.status === 'verifying' && (
          <>
            <div className="spinner" />
            <h1>{t('payment.verifying', 'در حال تأیید پرداخت...')}</h1>
            <p>{t('payment.dontClose', 'لطفاً این صفحه را نبندید.')}</p>
          </>
        )}

        {state.status === 'paid' && (
          <>
            <span className="result-icon"><Icon name="checkCircle" size={44} /></span>
            <h1>{t('payment.success', 'پرداخت با موفقیت انجام شد')}</h1>
            <p>{t('payment.successText', 'سفارش شما ثبت و تأیید شد. جزئیات ارسال را در صفحه سفارش ببینید.')}</p>
            <dl className="result-facts">
              <div><dt>{t('payment.orderNumber', 'شماره سفارش')}</dt><dd dir="ltr">{orderNumber}</dd></div>
              {state.refId && <div><dt>{t('payment.refId', 'کد پیگیری')}</dt><dd dir="ltr">{state.refId}</dd></div>}
              {state.order && <div><dt>{t('payment.amount', 'مبلغ')}</dt><dd><Price amount={state.order.total} /></dd></div>}
            </dl>
            <div className="empty-actions">
              <Link to={`/orders/${orderNumber}`} className="btn btn-primary">{t('payment.viewOrder', 'مشاهده سفارش')}</Link>
              <Link to="/products" className="btn btn-outline">{t('common.continueShopping')}</Link>
            </div>
          </>
        )}

        {state.status === 'failed' && (
          <>
            <span className="result-icon"><Icon name="close" size={44} /></span>
            <h1>{t('payment.failed', 'پرداخت ناموفق بود')}</h1>
            <p>{state.error}</p>
            <p className="muted">{t('payment.failedHelp', 'اگر مبلغی از حساب شما کسر شده، طی ۷۲ ساعت به حساب‌تان برمی‌گردد.')}</p>
            <div className="empty-actions">
              {orderNumber && <Link to={`/orders/${orderNumber}`} className="btn btn-primary">{t('payment.retry', 'تلاش دوباره')}</Link>}
              <Link to="/orders" className="btn btn-outline">{t('header.myOrders')}</Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
