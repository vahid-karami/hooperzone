import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { usePageMeta } from '../utils/seo';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { validateIranianPhone } from '../utils/iranianPhone';

export default function Register() {
  const { t } = useTranslation();
  usePageMeta({ title: t('common.register', 'ثبت‌نام'), noindex: true });
  const navigate = useNavigate();
  const { sendOTP, verifyOTP, register } = useAuth();
  const { success, error: showError } = useToast();

  const [authMethod, setAuthMethod] = useState('direct'); // 'direct' (username & password) or 'otp'
  const [identifier, setIdentifier] = useState('');
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    password: '',
    password_confirm: '',
  });

  // OTP state
  const [otpStep, setOtpStep] = useState('phone');
  const [otpPhone, setOtpPhone] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [otpPassword, setOtpPassword] = useState('');
  const [otpFirstName, setOtpFirstName] = useState('');
  const [otpLastName, setOtpLastName] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // 1. Direct username & password registration
  const handleDirectRegister = async (e) => {
    e.preventDefault();
    const cleanIdentifier = identifier.trim();

    if (!cleanIdentifier) {
      setError(t('auth.usernameOrPhone', 'نام کاربری یا شماره موبایل') + ' ' + t('common.required', 'الزامی است'));
      return;
    }

    if (cleanIdentifier.length < 3) {
      setError(t('auth.identifierMin', 'نام کاربری باید حداقل ۳ کاراکتر باشد'));
      return;
    }

    const isPhoneLike = /^(\+98|0)?9\d*$/.test(cleanIdentifier);
    if (isPhoneLike && !validateIranianPhone(cleanIdentifier)) {
      setError(t('auth.invalidPhone', 'لطفاً شماره موبایل معتبر وارد کنید'));
      return;
    }

    if (!formData.password || formData.password.length < 8) {
      setError(t('auth.minChars', 'رمز عبور باید حداقل ۸ کاراکتر باشد'));
      return;
    }

    if (formData.password !== formData.password_confirm) {
      setError(t('auth.passwordMismatch', 'رمز عبور و تکرار آن یکسان نیستند'));
      return;
    }

    setLoading(true);
    setError('');

    try {
      await register({
        username: cleanIdentifier,
        phone: cleanIdentifier,
        password: formData.password,
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim(),
      });
      success(t('auth.registrationSuccess', 'ثبت‌نام با موفقیت انجام شد!'));
      navigate('/');
    } catch (err) {
      const respData = err.response?.data;
      let message = 'ثبت‌نام ناموفق بود';
      if (typeof respData === 'object') {
        message =
          respData?.error ||
          respData?.username?.[0] ||
          respData?.phone?.[0] ||
          respData?.password?.[0] ||
          respData?.non_field_errors?.[0] ||
          t('auth.registrationFailed', 'ثبت‌نام انجام نشد. لطفاً اطلاعات را بررسی کنید.');
      }
      setError(message);
      showError(message);
    } finally {
      setLoading(false);
    }
  };

  // 2. OTP Registration handlers
  const handleSendOTP = async (e) => {
    e.preventDefault();
    if (!otpPhone) {
      setError(t('auth.phoneNumber', 'شماره تلفن') + ' ' + t('common.required', 'الزامی است'));
      return;
    }
    if (!validateIranianPhone(otpPhone)) {
      setError(t('auth.invalidPhone', 'لطفاً شماره موبایل معتبر وارد کنید'));
      return;
    }
    setLoading(true);
    setError('');
    try {
      await sendOTP(otpPhone, 'register');
      setOtpStep('otp');
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
    if (!otpCode || otpCode.length !== 6) {
      setError(t('auth.invalidCode', 'لطفاً کد ۶ رقمی را وارد کنید'));
      return;
    }
    setLoading(true);
    setError('');
    try {
      await verifyOTP(otpPhone, otpCode, 'register');
      setOtpStep('details');
    } catch (err) {
      const message = err.response?.data?.error || t('auth.invalidOtp', 'کد تایید نامعتبر است');
      setError(message);
      showError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleOtpRegister = async (e) => {
    e.preventDefault();
    if (!otpPassword || otpPassword.length < 8) {
      setError(t('auth.minChars', 'رمز عبور باید حداقل ۸ کاراکتر باشد'));
      return;
    }
    setLoading(true);
    setError('');
    try {
      await register({
        phone: otpPhone,
        username: otpPhone,
        password: otpPassword,
        first_name: otpFirstName.trim(),
        last_name: otpLastName.trim(),
      });
      success(t('auth.registrationSuccess', 'ثبت‌نام با موفقیت انجام شد!'));
      navigate('/');
    } catch (err) {
      const message = err.response?.data?.error || t('auth.registrationFailed', 'ثبت‌نام ناموفق بود');
      setError(message);
      showError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <h1 className="auth-title">{t('auth.createAccount', 'ایجاد حساب کاربری')}</h1>
            <p className="auth-subtitle">
              {t('auth.registerSubtitle', 'جهت ثبت سفارش و خرید، حساب کاربری ایجاد کنید')}
            </p>
          </div>

          {error && <div className="error-message">{error}</div>}

          <div className="auth-method-switcher">
            <button
              type="button"
              onClick={() => setAuthMethod('direct')}
              className={`method-btn ${authMethod === 'direct' ? 'active' : ''}`}
            >
              {t('auth.loginWithPassword', 'ثبت‌نام با رمز عبور')}
            </button>
            <button
              type="button"
              onClick={() => setAuthMethod('otp')}
              className={`method-btn ${authMethod === 'otp' ? 'active' : ''}`}
            >
              {t('auth.loginWithOTP', 'ثبت‌نام با پیامک')}
            </button>
          </div>

          {authMethod === 'direct' ? (
            <form onSubmit={handleDirectRegister}>
              <div className="form-group">
                <label htmlFor="identifier" className="form-label">
                  {t('auth.usernameOrPhone', 'نام کاربری یا شماره موبایل')}
                </label>
                <input
                  type="text"
                  id="identifier"
                  placeholder="مثال: 09121234567 یا نام کاربری دلخواه"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  className="form-input"
                  dir="ltr"
                  autoComplete="username"
                  required
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label htmlFor="first_name" className="form-label">
                    {t('auth.firstName', 'نام')} <small style={{ color: 'var(--text-muted)' }}>(اختیاری)</small>
                  </label>
                  <input
                    type="text"
                    id="first_name"
                    placeholder={t('auth.firstName', 'نام')}
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    className="form-input"
                    autoComplete="given-name"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="last_name" className="form-label">
                    {t('auth.lastName', 'نام خانوادگی')} <small style={{ color: 'var(--text-muted)' }}>(اختیاری)</small>
                  </label>
                  <input
                    type="text"
                    id="last_name"
                    placeholder={t('auth.lastName', 'نام خانوادگی')}
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    className="form-input"
                    autoComplete="family-name"
                  />
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="password" className="form-label">
                  {t('auth.password', 'رمز عبور')}
                </label>
                <input
                  type="password"
                  id="password"
                  placeholder={t('auth.minChars', 'حداقل ۸ کاراکتر')}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  className="form-input"
                  autoComplete="new-password"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="password_confirm" className="form-label">
                  {t('auth.confirmPassword', 'تکرار رمز عبور')}
                </label>
                <input
                  type="password"
                  id="password_confirm"
                  placeholder={t('auth.confirmPassword', 'تکرار رمز عبور')}
                  value={formData.password_confirm}
                  onChange={(e) => setFormData({ ...formData, password_confirm: e.target.value })}
                  className="form-input"
                  autoComplete="new-password"
                  required
                />
              </div>

              <button type="submit" disabled={loading} className="btn btn-primary btn-lg btn-full">
                {loading ? t('common.loading', 'در حال ایجاد حساب...') : t('auth.createAccount', 'ثبت‌نام و ورود')}
              </button>
            </form>
          ) : (
            <>
              {otpStep === 'phone' && (
                <form onSubmit={handleSendOTP}>
                  <div className="form-group">
                    <label htmlFor="otpPhone" className="form-label">
                      {t('auth.phoneNumber', 'شماره موبایل')}
                    </label>
                    <input
                      type="tel"
                      id="otpPhone"
                      placeholder="مثال: 09121234567"
                      value={otpPhone}
                      onChange={(e) => setOtpPhone(e.target.value)}
                      className="form-input"
                      dir="ltr"
                      required
                    />
                  </div>
                  <button type="submit" disabled={loading} className="btn btn-primary btn-lg btn-full">
                    {loading ? t('common.loading', 'در حال ارسال...') : t('auth.sendOTP', 'ارسال کد تأیید')}
                  </button>
                </form>
              )}

              {otpStep === 'otp' && (
                <form onSubmit={handleVerifyOTP}>
                  <div className="form-group">
                    <label htmlFor="otpCode" className="form-label">
                      {t('auth.verificationCode', 'کد تأیید')}
                    </label>
                    <input
                      type="text"
                      id="otpCode"
                      placeholder="۶ رقم کد تایید"
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value)}
                      maxLength={6}
                      className="form-input otp-input"
                      required
                    />
                    <small style={{ color: 'var(--text-muted)', display: 'block', marginTop: '0.25rem' }}>
                      {t('auth.otpSentTo', 'کد ارسال شد به')} {otpPhone}
                    </small>
                  </div>
                  <button type="submit" disabled={loading} className="btn btn-primary btn-lg btn-full">
                    {loading ? t('common.loading', 'در حال بررسی...') : t('auth.verifyOTP', 'تأیید کد')}
                  </button>
                  <button
                    type="button"
                    onClick={() => setOtpStep('phone')}
                    className="btn btn-ghost btn-sm btn-full"
                    style={{ marginTop: '0.5rem' }}
                  >
                    {t('auth.changePhone', 'ویرایش شماره موبایل')}
                  </button>
                </form>
              )}

              {otpStep === 'details' && (
                <form onSubmit={handleOtpRegister}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <div className="form-group">
                      <label htmlFor="otpFirstName" className="form-label">
                        {t('auth.firstName', 'نام')}
                      </label>
                      <input
                        type="text"
                        id="otpFirstName"
                        placeholder={t('auth.firstName', 'نام')}
                        value={otpFirstName}
                        onChange={(e) => setOtpFirstName(e.target.value)}
                        className="form-input"
                      />
                    </div>
                    <div className="form-group">
                      <label htmlFor="otpLastName" className="form-label">
                        {t('auth.lastName', 'نام خانوادگی')}
                      </label>
                      <input
                        type="text"
                        id="otpLastName"
                        placeholder={t('auth.lastName', 'نام خانوادگی')}
                        value={otpLastName}
                        onChange={(e) => setOtpLastName(e.target.value)}
                        className="form-input"
                      />
                    </div>
                  </div>
                  <div className="form-group">
                    <label htmlFor="otpPassword" className="form-label">
                      {t('auth.password', 'رمز عبور')}
                    </label>
                    <input
                      type="password"
                      id="otpPassword"
                      placeholder={t('auth.minChars', 'حداقل ۸ کاراکتر')}
                      value={otpPassword}
                      onChange={(e) => setOtpPassword(e.target.value)}
                      className="form-input"
                      required
                    />
                  </div>
                  <button type="submit" disabled={loading} className="btn btn-primary btn-lg btn-full">
                    {loading ? t('common.loading', 'در حال ثبت‌نام...') : t('common.register', 'تکمیل ثبت‌نام')}
                  </button>
                </form>
              )}
            </>
          )}

          <div className="auth-footer">
            <p>
              {t('auth.alreadyHaveAccount', 'قبلاً حساب کاربری دارید؟')}{' '}
              <Link to="/login">{t('common.login', 'ورود')}</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
