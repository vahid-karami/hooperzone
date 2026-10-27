import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import AccountLayout from '../components/AccountLayout';
import Icon from '../components/Icon';
import { formatDate } from '../utils/persianDate';
import { IRANIAN_PROVINCES, validateIranianPostalCode } from '../utils/iranianAddress';
import { toEnglishDigits } from '../utils/digits';
import { toPersianNumber } from '../hooks/useLanguage';
import { usePageMeta } from '../utils/seo';

const EMPTY = { first_name: '', last_name: '', email: '', province: '', city: '', postal_code: '', address: '' };

export default function Profile() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const { user, updateProfile } = useAuth();
  const { success, error: showError } = useToast();
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  usePageMeta({ title: t('header.myAccount'), noindex: true });

  useEffect(() => {
    if (!user) return;
    setForm({
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      email: user.email || '',
      province: user.province || '',
      city: user.city || '',
      postal_code: user.postal_code || '',
      address: user.address || '',
    });
  }, [user]);

  const province = IRANIAN_PROVINCES.find((p) => p.name === form.province);
  const dirty = user && Object.keys(EMPTY).some((k) => (user[k] || '') !== form[k]);

  const setField = (name, value) => {
    setForm((f) => ({ ...f, [name]: value }));
    setErrors((e) => ({ ...e, [name]: undefined }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const next = {};
    if (form.postal_code && !validateIranianPostalCode(form.postal_code)) next.postal_code = t('checkout.invalidPostalCode');
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) next.email = t('profile.invalidEmail', 'ایمیل معتبر نیست');
    setErrors(next);
    if (Object.keys(next).length) return;

    setSaving(true);
    try {
      await updateProfile({ ...form, postal_code: toEnglishDigits(form.postal_code).replace(/[\s-]/g, '') });
      success(t('profile.updateSuccess'));
    } catch (err) {
      const data = err.response?.data;
      if (data && typeof data === 'object' && !data.error) {
        setErrors(Object.fromEntries(Object.entries(data).map(([k, v]) => [k, [].concat(v).join(' ')])));
      }
      showError(data?.error || t('profile.updateFailed'));
    } finally {
      setSaving(false);
    }
  };

  const field = (name, label, props = {}) => (
    <div className="form-group">
      <label className="form-label" htmlFor={name}>{label}</label>
      <input
        id={name}
        name={name}
        value={form[name]}
        onChange={(e) => setField(name, e.target.value)}
        className={`form-input ${errors[name] ? 'has-error' : ''}`}
        aria-invalid={Boolean(errors[name])}
        {...props}
      />
      {errors[name] && <p className="field-error">{errors[name]}</p>}
    </div>
  );

  return (
    <AccountLayout title={t('header.myAccount')}>
      <form onSubmit={handleSubmit} className="account-sections" noValidate>
        <section className="form-card">
          <h2><Icon name="user" size={20} /> {t('profile.personalInfo', 'اطلاعات شخصی')}</h2>
          <div className="form-grid two">
            {field('first_name', t('auth.firstName'), { autoComplete: 'given-name' })}
            {field('last_name', t('auth.lastName'), { autoComplete: 'family-name' })}
            {field('email', t('profile.email', 'ایمیل'), { type: 'email', dir: 'ltr', autoComplete: 'email', placeholder: 'name@example.com' })}
            <div className="form-group">
              <span className="form-label">{t('auth.phoneNumber')}</span>
              <p className="readonly-field" dir="ltr">{lang === 'fa' ? toPersianNumber(user?.phone || '') : user?.phone}</p>
            </div>
          </div>
        </section>

        <section className="form-card">
          <h2><Icon name="truck" size={20} /> {t('profile.defaultAddress', 'نشانی پیش‌فرض ارسال')}</h2>
          <p className="muted card-hint">{t('profile.addressHint', 'این نشانی هنگام خرید به‌صورت خودکار پر می‌شود.')}</p>
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label" htmlFor="province">{t('checkout.state')}</label>
              <select
                id="province"
                value={form.province}
                onChange={(e) => {
                  setField('province', e.target.value);
                  setField('city', '');
                }}
                className="form-select"
              >
                <option value="">{t('checkout.selectProvince')}</option>
                {IRANIAN_PROVINCES.map((p) => (
                  <option key={p.id} value={p.name}>{lang === 'fa' ? p.name : p.name_en}</option>
                ))}
              </select>
            </div>
            {field('city', t('checkout.city'), { list: 'profile-cities', autoComplete: 'address-level2' })}
            <datalist id="profile-cities">
              {(province?.cities || []).map((c) => <option key={c} value={c} />)}
            </datalist>
            {field('postal_code', t('checkout.zipCode'), { inputMode: 'numeric', dir: 'ltr', maxLength: 12, placeholder: '1234567890' })}
          </div>
          <div className="form-group">
            <label className="form-label" htmlFor="address">{t('checkout.address')}</label>
            <textarea
              id="address"
              value={form.address}
              onChange={(e) => setField('address', e.target.value)}
              className="form-textarea"
              rows={3}
              placeholder={t('checkout.addressPlaceholder', 'خیابان، کوچه، پلاک، واحد')}
            />
          </div>
        </section>

        <div className="account-save">
          <p className="muted">
            {t('profile.memberSince')} {formatDate(user?.date_joined, lang)}
          </p>
          <button type="submit" className="btn btn-primary btn-lg" disabled={saving || !dirty}>
            {saving ? t('common.loading') : t('profile.saveChanges')}
          </button>
        </div>
      </form>
    </AccountLayout>
  );
}
