import { describe, it, expect } from 'vitest';
import { authErrorMessage, needsNewCode } from '../utils/authErrors';
import fa from '../i18n/locales/fa.json';
import en from '../i18n/locales/en.json';

const t = (key) => key;
const apiError = (status, data) => ({ response: { status, data } });

describe('authErrorMessage', () => {
  it('translates every code the server sends', () => {
    const cases = {
      user_not_found: 'auth.errUserNotFound',
      otp_invalid: 'auth.errOtpInvalid',
      otp_expired: 'auth.errOtpExpired',
      otp_locked: 'auth.errOtpLocked',
      sms_failed: 'auth.errSmsFailed',
    };
    for (const [code, key] of Object.entries(cases)) {
      expect(authErrorMessage(apiError(400, { error: 'English text', code }), t)).toBe(key);
      const name = key.replace('auth.', '');
      expect(fa.auth[name]).toBeTruthy();
      expect(en.auth[name]).toBeTruthy();
    }
  });

  it('explains a rate limit, which has no code', () => {
    expect(authErrorMessage(apiError(429, { detail: 'Request was throttled.' }), t)).toBe('auth.errTooMany');
  });

  it('uses the password rule texts for a refused password', () => {
    const data = { password: ['Too common.'], password_codes: ['password_too_common'] };
    expect(authErrorMessage(apiError(400, data), t)).toBe('auth.passwordTooCommon');
  });

  it('falls back to the server sentence, then to a general message', () => {
    expect(authErrorMessage(apiError(400, { error: 'Something new.', code: 'brand_new' }), t)).toBe('Something new.');
    expect(authErrorMessage(apiError(500, '<html>Server Error</html>'), t)).toBe('auth.errGeneric');
    expect(authErrorMessage(new Error('Network Error'), t)).toBe('auth.errGeneric');
  });
});

describe('needsNewCode', () => {
  it('is true only when the code can no longer work', () => {
    expect(needsNewCode(apiError(400, { code: 'otp_expired' }))).toBe(true);
    expect(needsNewCode(apiError(400, { code: 'otp_locked' }))).toBe(true);
    expect(needsNewCode(apiError(400, { code: 'otp_invalid' }))).toBe(false);
    expect(needsNewCode(new Error('Network Error'))).toBe(false);
  });
});
