import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import '../../i18n';
import fa from '../../i18n/locales/fa.json';
import Register from '../Register';

const sendOTP = vi.fn();
const verifyOTP = vi.fn();
const register = vi.fn();
const toastError = vi.fn();

vi.mock('../../context/AuthContext', () => ({ useAuth: () => ({ sendOTP, verifyOTP, register }) }));
vi.mock('../../context/ToastContext', () => ({ useToast: () => ({ success: vi.fn(), error: toastError }) }));
vi.mock('../../utils/seo', () => ({ usePageMeta: () => {} }));

const apiError = (status, data) => Object.assign(new Error('request failed'), { response: { status, data } });
const field = (id) => document.getElementById(id);
const type = (id, value) => fireEvent.change(field(id), { target: { value } });
const submit = (id) => fireEvent.submit(field(id).closest('form'));
const lastToast = () => toastError.mock.calls.at(-1)?.[0];

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/register']}>
      <Register />
    </MemoryRouter>,
  );
}

describe('Sign-up errors are shown in Persian, not as the API sentence', () => {
  beforeEach(() => {
    sendOTP.mockReset().mockResolvedValue({});
    verifyOTP.mockReset().mockResolvedValue({ registration_token: 'token-1' });
    register.mockReset().mockResolvedValue({});
    toastError.mockReset();
  });

  it('direct form: phone or username already used, refused password, rate limit', async () => {
    renderPage();
    const attempt = async (error, expected) => {
      register.mockRejectedValueOnce(error);
      type('identifier', 'sara_ahmadi');
      type('password', 'blue-Kettle-41');
      type('password_confirm', 'blue-Kettle-41');
      submit('password');
      await waitFor(() => expect(lastToast()).toBe(expected));
      expect(screen.getByText(expected)).toBeTruthy();
    };
    await attempt(apiError(400, { phone: ['A user with this phone number already exists.'], code: 'phone_exists' }), fa.auth.errPhoneExists);
    await attempt(apiError(400, { username: ['A user with this username already exists.'], code: 'username_exists' }), fa.auth.errUsernameExists);
    await attempt(apiError(400, { error: 'User already registered. Please login.', code: 'already_registered' }), fa.auth.errAlreadyRegistered);
    await attempt(apiError(400, { password: ['x'], password_codes: ['password_too_common'] }), fa.auth.passwordTooCommon);
    await attempt(apiError(429, { detail: 'Request was throttled.' }), fa.auth.errTooMany);
  });

  it('SMS sign-up: each step translates its error and the token is sent at the end', async () => {
    renderPage();
    fireEvent.click(screen.getByText(fa.auth.loginWithOTP));

    sendOTP.mockRejectedValueOnce(apiError(400, { error: 'A user with this phone number already exists.', code: 'phone_exists' }));
    type('otpPhone', '09121234567');
    submit('otpPhone');
    await waitFor(() => expect(lastToast()).toBe(fa.auth.errPhoneExists));

    submit('otpPhone');
    await waitFor(() => expect(field('otpCode')).toBeTruthy());

    verifyOTP.mockRejectedValueOnce(apiError(400, { error: 'Too many wrong codes.', code: 'otp_locked' }));
    type('otpCode', '123456');
    submit('otpCode');
    await waitFor(() => expect(lastToast()).toBe(fa.auth.errOtpLocked));
    expect(field('otpCode').value).toBe('');

    type('otpCode', '654321');
    submit('otpCode');
    await waitFor(() => expect(field('otpPassword')).toBeTruthy());

    register.mockRejectedValueOnce(apiError(400, { error: 'Please verify your phone number before registering.', code: 'phone_not_verified' }));
    type('otpPassword', 'blue-Kettle-41');
    submit('otpPassword');
    await waitFor(() => expect(lastToast()).toBe(fa.auth.errPhoneNotVerified));

    submit('otpPassword');
    await waitFor(() => expect(register).toHaveBeenCalledTimes(2));
    expect(register.mock.calls[1][0]).toMatchObject({ phone: '09121234567', registration_token: 'token-1' });
  });
});
