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
  invalid_credentials: ['auth.errInvalidCredentials', 'نام کاربری یا رمز عبور اشتباه است.'],
  identifier_required: ['auth.errIdentifierRequired', 'نام کاربری یا شماره موبایل را وارد کنید.'],
  phone_exists: ['auth.errPhoneExists', 'با این شماره موبایل قبلاً حساب ساخته شده است. وارد شوید.'],
  username_exists: ['auth.errUsernameExists', 'این نام کاربری قبلاً گرفته شده است. نام دیگری انتخاب کنید.'],
  already_registered: ['auth.errAlreadyRegistered', 'این حساب قبلاً ساخته شده است. وارد شوید.'],
  phone_not_verified: ['auth.errPhoneNotVerified', 'ابتدا شماره موبایل را با کد پیامکی تأیید کنید.'],
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
  return passwordErrorMessage(data, t) || serverSentence(data) || t('auth.errGeneric', 'مشکلی پیش آمد. دوباره تلاش کنید.');
}

// The server's own (English) sentence, for an error that has no code yet.
function serverSentence(data) {
  if (!data || typeof data !== 'object') return null;
  if (typeof data.error === 'string' && data.error) return data.error;
  for (const key of ['non_field_errors', 'username', 'phone', 'email', 'code']) {
    const value = Array.isArray(data[key]) ? data[key][0] : null;
    if (typeof value === 'string' && value) return value;
  }
  return null;
}
