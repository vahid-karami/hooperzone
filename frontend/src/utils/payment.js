import apiClient from '../api/client';
import { ENDPOINTS } from '../api/endpoints';

// IDPay is still supported by the backend; add it back here once IDPAY_API_KEY is configured.
export const GATEWAYS = [
  { key: 'zarinpal', fa: 'زرین‌پال', en: 'ZarinPal' },
];

/**
 * Ask the backend for a payment session and send the customer to the gateway.
 * The gateway (or the sandbox mock) returns them to /payment/result.
 */
export async function startPayment({ orderNumber, gateway, navigate }) {
  const callbackUrl = `${window.location.origin}/payment/result?order_number=${encodeURIComponent(orderNumber)}&gateway=${gateway}`;
  const { data } = await apiClient.post(ENDPOINTS.orderPay(orderNumber), { gateway, callback_url: callbackUrl });
  const target = new URL(data.payment_url, window.location.origin);
  if (target.origin === window.location.origin) {
    // Sandbox: we're sent straight back to our own result page.
    navigate(`${target.pathname}${target.search}`);
  } else {
    window.location.assign(target.href);
  }
}
