// Password rules shown to customers. The server decides (accounts/passwords.py runs Django's
// password validators); this file turns its rule codes into our own texts and catches the two
// rules that need no server (length, digits only) before the form is sent.

// Django rule code -> [i18n key, Persian default]
const MESSAGES = {
  password_too_short: ['auth.passwordTooShort', 'رمز عبور باید حداقل ۸ کاراکتر باشد.'],
  password_entirely_numeric: ['auth.passwordAllDigits', 'رمز عبور نباید فقط عدد باشد؛ حرف هم اضافه کنید.'],
  password_too_common: ['auth.passwordTooCommon', 'این رمز عبور خیلی رایج و قابل حدس است. رمز دیگری انتخاب کنید.'],
  password_too_similar: ['auth.passwordTooSimilar', 'رمز عبور نباید شبیه نام کاربری یا نام شما باشد.'],
};

// The most useful message first when several rules fail ("12345678" is both common and digits).
const ORDER = ['password_too_short', 'password_entirely_numeric', 'password_too_similar', 'password_too_common'];

export const MIN_PASSWORD_LENGTH = 8;

/** Rule code a password breaks without asking the server, or null. Persian digits count as digits. */
export function localPasswordProblem(password) {
  if (!password || password.length < MIN_PASSWORD_LENGTH) return 'password_too_short';
  if (/^[0-9۰-۹٠-٩]+$/.test(password)) return 'password_entirely_numeric';
  return null;
}

/** Translated message for one rule code, or null for a code we don't know. */
export function passwordRuleMessage(code, t) {
  const entry = MESSAGES[code];
  return entry ? t(entry[0], entry[1]) : null;
}

/**
 * Message for a refused password in an API error body, or null if the error isn't about the
 * password. Unknown codes fall back to the server's own (English) text.
 */
export function passwordErrorMessage(data, t) {
  if (!data || typeof data !== 'object') return null;
  const codes = Array.isArray(data.password_codes) ? data.password_codes : [];
  const known = ORDER.find((code) => codes.includes(code));
  if (known) return passwordRuleMessage(known, t);
  const text = Array.isArray(data.password) ? data.password[0] : data.password;
  return text || null;
}
