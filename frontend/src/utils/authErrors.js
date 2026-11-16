// Turns an error from the auth API into text in the customer's language. The server sends a
// stable `code` with each error (accounts/views.py error_response); its English `error`
// sentence is only a last resort.
import { passwordErrorMessage } from './passwordRules';

// API error code -> [i18n key, Persian default]
const MESSAGES = {
  user_not_found: ['auth.errUserNotFound', 'حسابی با این شماره موبایل پیدا نشد.'],
  otp_invalid: ['auth.errOtpInvalid', 'کد تأیید درست نیست.'],
  otp_expired: ['auth.errOtpExpired', 'مهلت این کد تمام شده است. کد تازه بگیرید.'],
  otp_locked: ['auth.errOtpLocked', 'کد چند بار اشتباه وارد شد و باطل شد. کد تازه بگیرید.'],
  sms_failed: ['auth.errSmsFailed', 'ارسال پیامک انجام نشد. چند دقیقه دیگر دوباره تلاش کنید.'],
};

/** True when the code in hand is dead and the customer needs a new one. */
export function needsNewCode(err) {
  return ['otp_expired', 'otp_locked'].includes(err?.response?.data?.code);
}

/** Message for a failed auth request (an axios error). */
export function authErrorMessage(err, t) {
  const response = err?.response;
  const data = response?.data;
  const entry = data && typeof data === 'object' ? MESSAGES[data.code] : null;
  if (entry) return t(entry[0], entry[1]);
  if (response?.status === 429) return t('auth.errTooMany', 'تعداد درخواست‌ها زیاد بود. کمی بعد دوباره تلاش کنید.');
  return (
    passwordErrorMessage(data, t) ||
    (data && typeof data === 'object' && typeof data.error === 'string' && data.error) ||
    t('auth.errGeneric', 'مشکلی پیش آمد. دوباره تلاش کنید.')
  );
}
