import { describe, it, expect } from 'vitest';
import { localPasswordProblem, passwordErrorMessage, passwordRuleMessage } from '../utils/passwordRules';
import fa from '../i18n/locales/fa.json';
import en from '../i18n/locales/en.json';

// Stand-in for i18next's t(): returns the key so tests don't depend on the wording.
const t = (key) => key;

describe('localPasswordProblem', () => {
  it('catches short and digit-only passwords, in Latin and Persian digits', () => {
    expect(localPasswordProblem('')).toBe('password_too_short');
    expect(localPasswordProblem('abc123')).toBe('password_too_short');
    expect(localPasswordProblem('12345678')).toBe('password_entirely_numeric');
    expect(localPasswordProblem('۱۲۳۴۵۶۷۸۹')).toBe('password_entirely_numeric');
  });

  it('lets other passwords through to the server', () => {
    expect(localPasswordProblem('blue-Kettle-41')).toBeNull();
    expect(localPasswordProblem('password')).toBeNull(); // only the server knows the common list
    expect(localPasswordProblem('کلمه‌عبور۱۲')).toBeNull();
  });
});

describe('passwordErrorMessage', () => {
  it('translates the server rule code', () => {
    const data = { password: ['This password is too common.'], password_codes: ['password_too_common'] };
    expect(passwordErrorMessage(data, t)).toBe('auth.passwordTooCommon');
  });

  it('picks the clearest message when several rules fail', () => {
    const data = { password: ['a', 'b'], password_codes: ['password_too_common', 'password_entirely_numeric'] };
    expect(passwordErrorMessage(data, t)).toBe('auth.passwordAllDigits');
  });

  it('falls back to the server text for a rule it does not know', () => {
    expect(passwordErrorMessage({ password: ['Needs a symbol.'], password_codes: ['needs_symbol'] }, t)).toBe('Needs a symbol.');
    expect(passwordErrorMessage({ password: ['Ensure this field has at least 8 characters.'] }, t)).toMatch(/8 characters/);
  });

  it('is null when the error is about something else', () => {
    expect(passwordErrorMessage({ error: 'User already registered. Please login.' }, t)).toBeNull();
    expect(passwordErrorMessage(undefined, t)).toBeNull();
    expect(passwordErrorMessage('Server error', t)).toBeNull();
  });
});

describe('texts', () => {
  it('every rule has Persian and English text', () => {
    const codes = ['password_too_short', 'password_entirely_numeric', 'password_too_common', 'password_too_similar'];
    for (const code of codes) {
      const key = passwordRuleMessage(code, t).replace('auth.', '');
      expect(fa.auth[key]).toBeTruthy();
      expect(en.auth[key]).toBeTruthy();
    }
    expect(fa.auth.passwordRules && en.auth.passwordRules).toBeTruthy();
  });
});
