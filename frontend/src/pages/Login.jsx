import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import AuthLayout from '../components/AuthLayout';
import { toEnglishDigits } from '../utils/digits';
import { validateIranianPhone } from '../utils/iranianPhone';
import { usePageMeta } from '../utils/seo';

export default function Login() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { sendOTP, verifyOTP, loginWithPassword } = useAuth();
  const { success, error: showError } = useToast();

  const [authMethod, setAuthMethod] = useState('password');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [step, setStep] = useState('phone');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  usePageMeta({ title: t('common.login', 'ورود'), noindex: true });

  const switchMethod = (method) => {
    setAuthMethod(method);
    setStep('phone');
    setError('');
  };

  const handleSendOTP = async (e) => {
    e.preventDefault();
    const number = toEnglishDigits(phone).trim();
    if (!number) {
      setError(t('auth.phoneNumber', 'شماره تلفن') + ' ' + t('common.required', 'الزامی است'));
      return;
    }
    if (!validateIranianPhone(number)) {
      setError(t('auth.invalidPhone', 'لطفاً شماره موبایل معتبر وارد کنید'));
      return;
    }
    setLoading(true);
    setError('');
    try {
      await sendOTP(number, 'login');
      setStep('otp');
      success(t('auth.otpSent', 'کد تایید ارسال شد'));
    } catch (err) {
      const message = err.response?.data?.error || t('auth.otpSendFailed', 'ارسال کد تایید ناموفق بود');
      setError(message);
      showError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOTP = async (e) => {
    e.preventDefault();
    const digits = toEnglishDigits(code).trim();
    if (digits.length !== 6) {
      setError(t('auth.invalidCode', 'لطفاً کد ۶ رقمی را وارد کنید'));
      return;
    }
    setLoading(true);
    setError('');
    try {
      await verifyOTP(toEnglishDigits(phone).trim(), digits, 'login');
      success(t('auth.loginSuccess', 'ورود موفقیت‌آمیز!'));
      navigate('/');
    } catch (err) {
      const message = err.response?.data?.error || t('auth.invalidOtp', 'کد تایید نامعتبر');
      setError(message);
      showError(message);
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordLogin = async (e) => {
    e.preventDefault();
    const identifier = toEnglishDigits(phone).trim();
    if (!identifier || !password) {
      setError(t('auth.fillFields', 'لطفاً تمام فیلدها را پر کنید'));
      return;
    }
    const isPhoneLike = /^(\+98|0)?9\d*$/.test(identifier);
    if (isPhoneLike && !validateIranianPhone(identifier)) {
      setError(t('auth.invalidPhone', 'لطفاً شماره موبایل معتبر وارد کنید'));
      return;
    }
    setLoading(true);
    setError('');
    try {
      await loginWithPassword(identifier, password);
      success(t('auth.loginSuccess', 'ورود موفقیت‌آمیز!'));
      navigate('/');
    } catch (err) {
      const message =
        err.response?.data?.error ||
        err.response?.data?.non_field_errors?.[0] ||
        t('auth.invalidCredentials', 'نام کاربری یا رمز عبور اشتباه است');
      setError(message);
      showError(message);
    } finally {
      setLoading(false);
    }
  };

  const submitLabel = (idle, busy) => (loading ? <><span className="btn-spinner" aria-hidden="true" />{busy}</> : idle);

  return (
    <AuthLayout
      title={t('auth.welcomeBack', 'ورود به حساب کاربری')}
      subtitle={t('auth.loginSubtitle', 'برای پیگیری سفارش‌ها و خرید سریع‌تر وارد شوید.')}
      footer={
        <>
          {t('auth.dontHaveAccount', 'حساب کاربری ندارید؟')}{' '}
          <Link to="/register">{t('auth.registerLink', 'ثبت‌نام کنید')}</Link>
        </>
      }
    >
      <div className="auth-tabs" role="tablist" aria-label={t('auth.method', 'روش ورود')}>
        {[
          ['password', t('auth.loginWithPassword', 'ورود با رمز عبور')],
          ['otp', t('auth.loginWithOTPShort', 'کد یکبار مصرف')],
        ].map(([method, label]) => (
          <button
            key={method}
            type="button"
            role="tab"
            aria-selected={authMethod === method}
            className={authMethod === method ? 'active' : ''}
            onClick={() => switchMethod(method)}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <div className="auth-error" role="alert">{error}</div>}

      {authMethod === 'password' && (
        <form onSubmit={handlePasswordLogin} className="auth-form" noValidate>
          <div className="auth-field">
            <label htmlFor="identifier">{t('auth.usernameOrPhone', 'نام کاربری یا شماره موبایل')}</label>
            <input
              id="identifier"
              type="text"
              inputMode="text"
              placeholder="09121234567"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              dir="ltr"
              autoComplete="username"
              aria-invalid={Boolean(error) || undefined}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="password">{t('auth.password', 'رمز عبور')}</label>
            <input
              id="password"
              type="password"
              placeholder={t('auth.passwordPlaceholder', 'رمز عبور خود را وارد کنید')}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              dir="ltr"
              autoComplete="current-password"
              aria-invalid={Boolean(error) || undefined}
            />
          </div>
          <button type="submit" disabled={loading} className="auth-submit">
            {submitLabel(t('common.login', 'ورود'), t('auth.loggingIn', 'در حال ورود...'))}
          </button>
        </form>
      )}

      {authMethod === 'otp' && step === 'phone' && (
        <form onSubmit={handleSendOTP} className="auth-form" noValidate>
          <div className="auth-field">
            <label htmlFor="otp-phone">{t('auth.mobile', 'شماره موبایل')}</label>
            <input
              id="otp-phone"
              type="tel"
              inputMode="tel"
              placeholder="09121234567"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              dir="ltr"
              autoComplete="tel"
              aria-invalid={Boolean(error) || undefined}
            />
            <small>{t('auth.otpHint', 'کد تایید شش‌رقمی برای این شماره ارسال می‌شود.')}</small>
          </div>
          <button type="submit" disabled={loading} className="auth-submit">
            {submitLabel(t('auth.sendOTP', 'ارسال کد تأیید'), t('auth.sending', 'در حال ارسال...'))}
          </button>
        </form>
      )}

      {authMethod === 'otp' && step === 'otp' && (
        <form onSubmit={handleVerifyOTP} className="auth-form" noValidate>
          <div className="auth-field">
            <label htmlFor="otp-code">{t('auth.verificationCode', 'کد تأیید')}</label>
            <input
              id="otp-code"
              type="text"
              inputMode="numeric"
              placeholder="------"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              maxLength={6}
              dir="ltr"
              className="otp-code"
              autoComplete="one-time-code"
              aria-invalid={Boolean(error) || undefined}
              autoFocus
            />
            <small>
              {t('auth.otpSentTo', 'کد ارسال شد به')} <bdi dir="ltr">{toEnglishDigits(phone).trim()}</bdi>
            </small>
          </div>
          <button type="submit" disabled={loading} className="auth-submit">
            {submitLabel(t('auth.verifyLogin', 'تأیید و ورود'), t('auth.verifying', 'در حال بررسی...'))}
          </button>
          <button type="button" className="auth-link-btn" onClick={() => { setStep('phone'); setCode(''); setError(''); }}>
            {t('auth.changePhone', 'تغییر شماره موبایل')}
          </button>
        </form>
      )}
    </AuthLayout>
  );
}
