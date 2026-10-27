// Order and payment status labels (the API returns English display names).
export const ORDER_STEPS = ['pending', 'confirmed', 'processing', 'shipped', 'delivered'];

const STATUS = {
  pending: { fa: 'در انتظار پرداخت', en: 'Awaiting payment', tone: 'warn' },
  confirmed: { fa: 'تأیید شده', en: 'Confirmed', tone: 'info' },
  processing: { fa: 'در حال آماده‌سازی', en: 'Processing', tone: 'info' },
  shipped: { fa: 'ارسال شده', en: 'Shipped', tone: 'info' },
  delivered: { fa: 'تحویل شده', en: 'Delivered', tone: 'ok' },
  cancelled: { fa: 'لغو شده', en: 'Cancelled', tone: 'bad' },
};

const PAYMENT = {
  pending: { fa: 'پرداخت نشده', en: 'Unpaid', tone: 'warn' },
  paid: { fa: 'پرداخت شده', en: 'Paid', tone: 'ok' },
  failed: { fa: 'پرداخت ناموفق', en: 'Payment failed', tone: 'bad' },
  refunded: { fa: 'بازگشت وجه', en: 'Refunded', tone: 'info' },
};

const pick = (table, key, lang) => {
  const entry = table[key];
  return entry ? { label: lang === 'fa' ? entry.fa : entry.en, tone: entry.tone } : { label: key, tone: 'info' };
};

export const orderStatus = (key, lang) => pick(STATUS, key, lang);
export const paymentStatus = (key, lang) => pick(PAYMENT, key, lang);

export const canPay = (order) => order.payment_status !== 'paid' && order.status !== 'cancelled';
export const canCancel = (order) => ['pending', 'confirmed'].includes(order.status);

export const SHIPPING_METHODS = ['post', 'pishtaz', 'tipax'];

const SHIPPING = {
  post: { fa: 'پست سفارشی', en: 'Post (registered)' },
  pishtaz: { fa: 'پست پیشتاز', en: 'Post Pishtaz' },
  tipax: { fa: 'تیپاکس', en: 'Tipax' },
};

export const shippingMethodLabel = (key, lang) => (SHIPPING[key] ? SHIPPING[key][lang === 'fa' ? 'fa' : 'en'] : key || '—');

// Public tracking pages for a parcel's tracking code.
export const trackingUrl = (method) =>
  method === 'tipax' ? 'https://tipaxco.com/tracking' : 'https://tracking.post.ir/';
