import { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import Price from '../components/Price';
import Icon from '../components/Icon';
import Breadcrumbs from '../components/Breadcrumbs';
import LoadingSpinner from '../components/LoadingSpinner';
import { validateIranianPhone } from '../utils/iranianPhone';
import { IRANIAN_PROVINCES, validateIranianPostalCode } from '../utils/iranianAddress';
import { toEnglishDigits } from '../utils/digits';
import { GATEWAYS, startPayment } from '../utils/payment';
import { toPersianNumber } from '../hooks/useLanguage';
import { usePageMeta } from '../utils/seo';

function Steps({ current }) {
  const { t } = useTranslation();
  const steps = [t('checkout.stepCart', 'سبد خرید'), t('checkout.stepShipping', 'اطلاعات ارسال'), t('checkout.stepPayment', 'پرداخت')];
  return (
    <ol className="checkout-steps">
      {steps.map((label, i) => (
        <li key={label} className={i < current ? 'done' : i === current ? 'current' : ''} aria-current={i === current ? 'step' : undefined}>
          <span className="step-dot">{i < current ? <Icon name="check" size={14} strokeWidth={2.4} /> : i + 1}</span>
          {label}
        </li>
      ))}
    </ol>
  );
}

export default function Checkout() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const navigate = useNavigate();
  const { cart, loading: cartLoading, refreshCart } = useCart();
  const { user, isAuthenticated, loading: authLoading } = useAuth();
  const { error: showError } = useToast();

  usePageMeta({ title: t('checkout.title') });

  // Prefilled from the profile; the user can edit everything.
  const [form, setForm] = useState(() => ({
    shipping_phone: user?.phone || '',
    shipping_state: user?.province || '',
    shipping_city: user?.city || '',
    shipping_zip: user?.postal_code || '',
    shipping_address: user?.address || '',
    notes: '',
  }));
  const [gateway, setGateway] = useState('zarinpal');
  const [shippingMethods, setShippingMethods] = useState([]);
  const [shippingMethod, setShippingMethod] = useState('post');

  // Fees are set by staff in the admin portal; the backend charges the same amount.
  useEffect(() => {
    apiClient
      .get(ENDPOINTS.shippingMethods)
      .then(({ data }) => setShippingMethods(data))
      .catch(() => setShippingMethods([]));
  }, []);

  // The profile loads after the first render on a hard reload; fill only empty fields.
  useEffect(() => {
    if (!user) return;
    setForm((f) => ({
      ...f,
      shipping_phone: f.shipping_phone || user.phone || '',
      shipping_state: f.shipping_state || user.province || '',
      shipping_city: f.shipping_city || user.city || '',
      shipping_zip: f.shipping_zip || user.postal_code || '',
      shipping_address: f.shipping_address || user.address || '',
    }));
  }, [user]);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const province = IRANIAN_PROVINCES.find((p) => p.name === form.shipping_state);

  const setField = (name, value) => {
    setForm((f) => ({ ...f, [name]: value }));
    setErrors((e) => ({ ...e, [name]: undefined }));
  };

  const validate = () => {
    const next = {};
    if (!validateIranianPhone(form.shipping_phone)) next.shipping_phone = t('auth.invalidPhone');
    if (!form.shipping_state) next.shipping_state = t('common.required', 'الزامی است');
    if (!form.shipping_city.trim()) next.shipping_city = t('common.required', 'الزامی است');
    if (!validateIranianPostalCode(form.shipping_zip)) next.shipping_zip = t('checkout.invalidPostalCode');
    if (form.shipping_address.trim().length < 10) next.shipping_address = t('checkout.addressTooShort', 'نشانی را کامل‌تر بنویسید (حداقل ۱۰ حرف).');
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) {
      document.querySelector('.field-error')?.closest('.form-group')?.querySelector('input,select,textarea')?.focus();
      return;
    }
    setSubmitting(true);
    let orderNumber;
    try {
      const { data } = await apiClient.post(ENDPOINTS.orderCreate, {
        ...form,
        shipping_phone: toEnglishDigits(form.shipping_phone),
        shipping_zip: toEnglishDigits(form.shipping_zip).replace(/[\s-]/g, ''),
        shipping_country: 'IR',
        shipping_method: shippingMethod,
      });
      orderNumber = data.order_number;
      refreshCart();
      await startPayment({ orderNumber, gateway, navigate });
    } catch (err) {
      const message = err.response?.data?.error || t('checkout.orderFailed');
      showError(message);
      // The order exists but payment couldn't start: let them retry from the order page.
      if (orderNumber) navigate(`/orders/${orderNumber}`);
      setSubmitting(false);
    }
  };

  if (authLoading) return <LoadingSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (cartLoading || cart.id === undefined) return <LoadingSpinner />;
  if (!cart.items || cart.items.length === 0) return <Navigate to="/cart" replace />;

  const subtotal = Number(cart.total_price) || 0;
  const selectedMethod = shippingMethods.find((m) => m.code === shippingMethod);
  const shipping = selectedMethod ? Number(selectedMethod.fee) : null;
  const total = subtotal + (shipping || 0);
  const itemName = (p) => (lang === 'fa' && p.name_fa) || p.name_localized || p.name;

  const fieldError = (name) =>
    errors[name] && (
      <p className="field-error" id={`${name}-error`}>
        {errors[name]}
      </p>
    );
  const fieldProps = (name) => ({
    id: name,
    name,
    value: form[name],
    onChange: (e) => setField(name, e.target.value),
    'aria-invalid': Boolean(errors[name]),
    'aria-describedby': errors[name] ? `${name}-error` : undefined,
    className: `form-input ${errors[name] ? 'has-error' : ''}`,
  });

  return (
    <div className="checkout-page">
      <div className="container">
        <Breadcrumbs items={[{ to: '/', label: t('common.home') }, { to: '/cart', label: t('cart.shoppingCart') }, { label: t('checkout.title') }]} />
        <h1 className="display-title">{t('checkout.title')}</h1>
        <Steps current={1} />

        <form className="checkout-layout" onSubmit={handleSubmit} noValidate>
          <div className="checkout-main">
            <section className="form-card">
              <h2><Icon name="phone" size={20} /> {t('checkout.contact', 'اطلاعات تماس')}</h2>
              <div className="form-group">
                <label className="form-label" htmlFor="shipping_phone">{t('checkout.phone')}</label>
                <input {...fieldProps('shipping_phone')} type="tel" inputMode="tel" dir="ltr" autoComplete="tel" placeholder="09123456789" />
                {fieldError('shipping_phone')}
              </div>
            </section>

            <section className="form-card">
              <h2><Icon name="truck" size={20} /> {t('checkout.shippingInfo')}</h2>
              <div className="form-grid">
                <div className="form-group">
                  <label className="form-label" htmlFor="shipping_state">{t('checkout.state')}</label>
                  <select
                    {...fieldProps('shipping_state')}
                    className={`form-select ${errors.shipping_state ? 'has-error' : ''}`}
                    onChange={(e) => {
                      setField('shipping_state', e.target.value);
                      setField('shipping_city', '');
                    }}
                  >
                    <option value="">{t('checkout.selectProvince')}</option>
                    {IRANIAN_PROVINCES.map((p) => (
                      <option key={p.id} value={p.name}>{lang === 'fa' ? p.name : p.name_en}</option>
                    ))}
                  </select>
                  {fieldError('shipping_state')}
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="shipping_city">{t('checkout.city')}</label>
                  {/* Suggest the province's main cities but allow any city. */}
                  <input {...fieldProps('shipping_city')} list="city-options" autoComplete="address-level2" placeholder={t('checkout.selectCity')} />
                  <datalist id="city-options">
                    {(province?.cities || []).map((c) => <option key={c} value={c} />)}
                  </datalist>
                  {fieldError('shipping_city')}
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="shipping_zip">{t('checkout.zipCode')}</label>
                  <input {...fieldProps('shipping_zip')} inputMode="numeric" dir="ltr" autoComplete="postal-code" placeholder="1234567890" maxLength={12} />
                  {fieldError('shipping_zip')}
                </div>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="shipping_address">{t('checkout.address')}</label>
                <textarea {...fieldProps('shipping_address')} className={`form-textarea ${errors.shipping_address ? 'has-error' : ''}`} rows={3} autoComplete="street-address" placeholder={t('checkout.addressPlaceholder', 'خیابان، کوچه، پلاک، واحد')} />
                {fieldError('shipping_address')}
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="notes">
                  {t('checkout.orderNotes')} <span className="optional">({t('checkout.optional', 'اختیاری')})</span>
                </label>
                <textarea {...fieldProps('notes')} className="form-textarea" rows={2} placeholder={t('checkout.notesPlaceholder')} />
              </div>
            </section>

            <section className="form-card">
              <h2><Icon name="box" size={20} /> {t('checkout.shippingMethod', 'روش ارسال')}</h2>
              <div className="gateway-options shipping-options" role="radiogroup" aria-label={t('checkout.shippingMethod', 'روش ارسال')}>
                {shippingMethods.map((m) => (
                  <label key={m.code} className={`gateway-option ${shippingMethod === m.code ? 'selected' : ''}`}>
                    <input type="radio" name="shipping_method" value={m.code} checked={shippingMethod === m.code} onChange={() => setShippingMethod(m.code)} />
                    <span className="gateway-name">{lang === 'fa' ? m.label_fa : m.label_en}</span>
                    <span className="gateway-note">
                      {t('checkout.deliveryDays', '{{days}} روز کاری', { days: num(String(m.days).replace('-', lang === 'fa' ? ' تا ' : '–')) })}
                    </span>
                    <span className="shipping-fee"><Price amount={m.fee} /></span>
                  </label>
                ))}
                {shippingMethods.length === 0 && <div className="skeleton shipping-skeleton" aria-hidden="true" />}
              </div>
            </section>

            <section className="form-card">
              <h2><Icon name="card" size={20} /> {t('checkout.paymentMethod', 'روش پرداخت')}</h2>
              <div className="gateway-options" role="radiogroup" aria-label={t('checkout.paymentMethod', 'روش پرداخت')}>
                {GATEWAYS.map((g) => (
                  <label key={g.key} className={`gateway-option ${gateway === g.key ? 'selected' : ''}`}>
                    <input type="radio" name="gateway" value={g.key} checked={gateway === g.key} onChange={() => setGateway(g.key)} />
                    <span className="gateway-name">{lang === 'fa' ? g.fa : g.en}</span>
                    <span className="gateway-note">{t('checkout.gatewayNote', 'پرداخت آنلاین با کلیه کارت‌های شتاب')}</span>
                  </label>
                ))}
              </div>
            </section>
          </div>

          <aside className="summary-card">
            <h2>{t('checkout.orderSummary')}</h2>
            <ul className="summary-items">
              {cart.items.map((item) => (
                <li key={item.id}>
                  <span className="summary-thumb">
                    {item.product.primary_image && <img src={item.product.primary_image.image} alt="" />}
                    <span className="summary-qty">{num(item.quantity)}</span>
                  </span>
                  <span className="summary-name">{itemName(item.product)}</span>
                  <Price amount={item.subtotal} />
                </li>
              ))}
            </ul>
            <dl className="summary-rows">
              <div><dt>{t('checkout.subtotal')}</dt><dd><Price amount={subtotal} /></dd></div>
              <div>
                <dt>{t('checkout.shipping')}</dt>
                <dd>{shipping === null ? '—' : <Price amount={shipping} />}</dd>
              </div>
              <div className="summary-total"><dt>{t('checkout.total')}</dt><dd><Price amount={total} /></dd></div>
            </dl>
            <button type="submit" disabled={submitting || !selectedMethod} className="btn btn-primary btn-lg btn-full">
              {submitting ? t('checkout.placingOrder') : t('checkout.payAndPlace', 'ثبت سفارش و پرداخت')}
            </button>
            <p className="summary-fineprint">
              <Icon name="shield" size={16} /> {t('checkout.secureNote', 'پس از ثبت سفارش به درگاه امن بانکی منتقل می‌شوید.')}
            </p>
          </aside>
        </form>
      </div>
    </div>
  );
}
