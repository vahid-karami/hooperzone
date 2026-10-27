import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import apiClient from '../../api/client';
import { ENDPOINTS } from '../../api/endpoints';
import { useToast } from '../../context/ToastContext';
import { toEnglishDigits } from '../../utils/digits';
import { usePageMeta } from '../../utils/seo';

const NUMBER_FIELDS = ['shipping_post', 'shipping_pishtaz', 'shipping_tipax', 'unpaid_order_timeout_minutes', 'low_stock_threshold'];

export default function AdminSettings() {
  const { t } = useTranslation();
  const { success, error: showError } = useToast();
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);

  usePageMeta({ title: t('admin.settings', 'تنظیمات فروشگاه'), noindex: true });

  useEffect(() => {
    apiClient
      .get(ENDPOINTS.adminSettings)
      .then((res) => setForm(res.data))
      .catch(() => showError(t('admin.loadFailed', 'بارگذاری اطلاعات انجام نشد')));
  }, [showError, t]);

  const setField = (name, value) => setForm((f) => ({ ...f, [name]: value }));

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    const payload = { ...form };
    delete payload.updated_at;
    NUMBER_FIELDS.forEach((k) => {
      payload[k] = parseInt(toEnglishDigits(String(payload[k] ?? '0')), 10) || 0;
    });
    try {
      const { data } = await apiClient.patch(ENDPOINTS.adminSettings, payload);
      setForm(data);
      success(t('admin.settingsSaved', 'تنظیمات ذخیره شد'));
    } catch (err) {
      const data = err.response?.data;
      showError(
        data && typeof data === 'object'
          ? Object.entries(data).map(([f, m]) => `${f}: ${[].concat(m).join(' ')}`).join(' — ')
          : t('admin.saveFailed', 'ذخیره انجام نشد'),
      );
    } finally {
      setSaving(false);
    }
  };

  if (!form) return <div className="loading"><div className="spinner" /></div>;

  const field = (name, label, props = {}, hint = '') => (
    <div className="form-group">
      <label className="form-label" htmlFor={`s-${name}`}>{label}</label>
      <input id={`s-${name}`} className="form-input" value={form[name] ?? ''} onChange={(e) => setField(name, e.target.value)} {...props} />
      {hint && <p className="field-hint">{hint}</p>}
    </div>
  );
  const money = { inputMode: 'numeric', dir: 'ltr' };

  return (
    <div className="admin-page">
      <header className="admin-page-head">
        <div>
          <h1>{t('admin.settings', 'تنظیمات فروشگاه')}</h1>
          <p className="muted">{t('admin.settingsHint', 'هزینه ارسال، اطلاعات تماس و نمادهای اعتماد')}</p>
        </div>
      </header>

      <form className="admin-form settings-form" onSubmit={save}>
        <section className="admin-card">
          <fieldset>
            <legend>{t('admin.shippingFees', 'هزینه ارسال (تومان)')}</legend>
            <div className="form-grid">
              {field('shipping_post', t('admin.shipPost', 'پست سفارشی'), money)}
              {field('shipping_pishtaz', t('admin.shipPishtaz', 'پست پیشتاز'), money)}
              {field('shipping_tipax', t('admin.shipTipax', 'تیپاکس'), money)}
            </div>
          </fieldset>
          <fieldset>
            <legend>{t('admin.orderRules', 'سفارش و موجودی')}</legend>
            <div className="form-grid">
              {field('unpaid_order_timeout_minutes', t('admin.unpaidTimeout', 'لغو خودکار سفارش پرداخت‌نشده (دقیقه)'), money, t('admin.unpaidTimeoutHint', 'موجودی رزروشده آزاد می‌شود. صفر یعنی هرگز.'))}
              {field('low_stock_threshold', t('admin.lowStockThreshold', 'هشدار کمبود موجودی از'), money)}
            </div>
          </fieldset>
        </section>

        <section className="admin-card">
          <fieldset>
            <legend>{t('admin.contactInfo', 'اطلاعات تماس فروشگاه')}</legend>
            <div className="form-grid two">
              {field('store_phone', t('admin.storePhone', 'تلفن'), { dir: 'ltr', inputMode: 'tel' })}
              {field('store_email', t('admin.storeEmail', 'ایمیل'), { dir: 'ltr', type: 'email' })}
              {field('instagram', t('admin.instagram', 'اینستاگرام (بدون @)'), { dir: 'ltr' })}
              {field('telegram', t('admin.telegram', 'تلگرام (بدون @)'), { dir: 'ltr' })}
              {field('whatsapp', t('admin.whatsapp', 'واتس‌اپ'), { dir: 'ltr', inputMode: 'tel' })}
              {field('working_hours', t('admin.workingHours', 'ساعات پاسخگویی'))}
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="s-address">{t('admin.storeAddress', 'نشانی')}</label>
              <textarea id="s-address" className="form-textarea" rows={2} value={form.store_address} onChange={(e) => setField('store_address', e.target.value)} />
            </div>
          </fieldset>
        </section>

        <section className="admin-card">
          <fieldset>
            <legend>{t('admin.trustBadges', 'نماد اعتماد الکترونیکی و ساماندهی')}</legend>
            <p className="field-hint">{t('admin.trustBadgesHint', 'کد HTML که سایت enamad.ir یا samandehi.ir به شما می‌دهد را اینجا بچسبانید. در پانویس سایت نمایش داده می‌شود.')}</p>
            <div className="form-grid two">
              <div className="form-group">
                <label className="form-label" htmlFor="s-enamad">{t('admin.enamad', 'کد اینماد')}</label>
                <textarea id="s-enamad" className="form-textarea mono" dir="ltr" rows={4} value={form.enamad_html} onChange={(e) => setField('enamad_html', e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="s-samandehi">{t('admin.samandehi', 'کد ساماندهی')}</label>
                <textarea id="s-samandehi" className="form-textarea mono" dir="ltr" rows={4} value={form.samandehi_html} onChange={(e) => setField('samandehi_html', e.target.value)} />
              </div>
            </div>
          </fieldset>
        </section>

        <div className="settings-actions">
          <button type="submit" className="btn btn-primary btn-lg" disabled={saving}>{saving ? t('common.loading') : t('admin.save', 'ذخیره')}</button>
        </div>
      </form>
    </div>
  );
}
