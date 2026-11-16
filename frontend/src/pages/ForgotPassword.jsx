import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import AuthLayout from '../components/AuthLayout';
import { toEnglishDigits } from '../utils/digits';
import { validateIranianPhone } from '../utils/iranianPhone';
import { usePageMeta } from '../utils/seo';
import { authErrorMessage, needsNewCode } from '../utils/authErrors';
import { localPasswordProblem, passwordRuleMessage } from '../utils/passwordRules';

// Forgot password: 1) phone -> a code by SMS, 2) code + new password -> back to login.
// The code and the new password go to the server together (one request); checking the code
// on its own first would use it up.
export default function ForgotPassword() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { sendOTP, resetPassword } = useAuth();
  const { success, error: showError } = useToast();

  const [step, setStep] = useState('phone');
  const [phone, setPhone] = useState(location.state?.phone || '');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  usePageMeta({ title: t('auth.forgotTitle', 'بازیابی رمز عبور'), noindex: true });

  const number = toEnglishDigits(phone).trim();
  // Keeps the page the customer was sent to login from (e.g. checkout).
  const loginLinkState = { ...location.state, phone: number || undefined };

  const fail = (message) => {
    setError(message);
    showError(message);
  };

  const handleSendCode = async (e) => {
    e.preventDefault();
    if (!validateIranianPhone(number)) {
      setError(t('auth.invalidPhone', 'لطفاً شماره موبایل معتبر وارد کنید'));
      return;
    }
    setLoading(true);
    setError('');
    try {
      await sendOTP(number, 'reset_password');
      setStep('reset');
      success(t('auth.otpSent', 'کد تایید ارسال شد'));
    } catch (err) {
      fail(authErrorMessage(err, t));
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (e) => {
    e.preventDefault();
    const digits = toEnglishDigits(code).trim();
    if (!/^\d{6}$/.test(digits)) {
      setError(t('auth.invalidCode', 'لطفاً کد ۶ رقمی را وارد کنید'));
      return;
    }
    const passwordProblem = localPasswordProblem(password);
    if (passwordProblem) {
      setError(passwordRuleMessage(passwordProblem, t));
      return;
    }
    if (password !== passwordConfirm) {
      setError(t('auth.passwordMismatch', 'رمز عبور و تکرار آن یکسان نیستند'));
      return;
    }
    setLoading(true);
    setError('');
    try {
      await resetPassword(number, digits, password);
      success(t('auth.passwordChanged', 'رمز عبور تغییر کرد. حالا با رمز جدید وارد شوید.'));
      navigate('/login', { replace: true, state: loginLinkState });
    } catch (err) {
      if (needsNewCode(err)) setCode('');
      fail(authErrorMessage(err, t));
    } finally {
      setLoading(false);
    }
  };

  const changePhone = () => {
    setStep('phone');
    setCode('');
    setError('');
  };

  const submitLabel = (idle, busy) => (loading ? <><span className="btn-spinner" aria-hidden="true" />{busy}</> : idle);

  return (
    <AuthLayout
      title={t('auth.forgotTitle', 'بازیابی رمز عبور')}
      subtitle={
        step === 'phone'
          ? t('auth.forgotSubtitle', 'شماره موبایل حساب خود را وارد کنید تا کد تأیید برایتان پیامک شود.')
          : t('auth.forgotCodeSubtitle', 'کد پیامک‌شده و رمز عبور جدید را وارد کنید.')
      }
      footer={
        <>
          {t('auth.rememberedPassword', 'رمز عبور را به خاطر آوردید؟')}{' '}
          <Link to="/login" state={loginLinkState}>{t('auth.backToLogin', 'بازگشت به ورود')}</Link>
        </>
      }
    >
      {error && <div className="auth-error" role="alert">{error}</div>}

      {step === 'phone' && (
        <form onSubmit={handleSendCode} className="auth-form" noValidate>
          <div className="auth-field">
            <label htmlFor="forgot-phone">{t('auth.mobile', 'شماره موبایل')}</label>
            <input
              id="forgot-phone"
              type="tel"
              inputMode="tel"
              placeholder="09121234567"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              dir="ltr"
              autoComplete="tel"
              aria-invalid={Boolean(error) || undefined}
              autoFocus
            />
            <small>{t('auth.otpHint', 'کد تایید شش‌رقمی برای این شماره ارسال می‌شود.')}</small>
          </div>
          <button type="submit" disabled={loading} className="auth-submit">
            {submitLabel(t('auth.sendOTP', 'ارسال کد تأیید'), t('auth.sending', 'در حال ارسال...'))}
          </button>
        </form>
      )}

      {step === 'reset' && (
        <form onSubmit={handleReset} className="auth-form" noValidate>
          <div className="auth-field">
            <label htmlFor="forgot-code">{t('auth.verificationCode', 'کد تأیید')}</label>
            <input
              id="forgot-code"
              type="text"
              inputMode="numeric"
              placeholder="------"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              maxLength={6}
              dir="ltr"
              className="otp-code"
              autoComplete="one-time-code"
              autoFocus
            />
            <small>
              {t('auth.otpSentTo', 'کد ارسال شد به')} <bdi dir="ltr">{number}</bdi>
            </small>
          </div>
          <div className="auth-field">
            <label htmlFor="forgot-password">{t('auth.newPassword', 'رمز عبور جدید')}</label>
            <input
              id="forgot-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              dir="ltr"
              autoComplete="new-password"
              aria-describedby="forgot-password-rules"
            />
            <small id="forgot-password-rules">
              {t('auth.passwordRules', 'حداقل ۸ کاراکتر؛ فقط عدد نباشد و رمز ساده‌ای مثل password انتخاب نکنید.')}
            </small>
          </div>
          <div className="auth-field">
            <label htmlFor="forgot-password-confirm">{t('auth.confirmNewPassword', 'تکرار رمز عبور جدید')}</label>
            <input
              id="forgot-password-confirm"
              type="password"
              value={passwordConfirm}
              onChange={(e) => setPasswordConfirm(e.target.value)}
              dir="ltr"
              autoComplete="new-password"
            />
          </div>
          <button type="submit" disabled={loading} className="auth-submit">
            {submitLabel(t('auth.savePassword', 'ذخیره رمز عبور جدید'), t('auth.saving', 'در حال ذخیره...'))}
          </button>
          <button type="button" className="auth-link-btn" onClick={changePhone}>
            {t('auth.changePhone', 'تغییر شماره موبایل')}
          </button>
        </form>
      )}
    </AuthLayout>
  );
}
