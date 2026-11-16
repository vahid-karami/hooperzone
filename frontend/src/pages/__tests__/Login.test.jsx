import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import '../../i18n';
import fa from '../../i18n/locales/fa.json';
import Login from '../Login';

const sendOTP = vi.fn();
const verifyOTP = vi.fn();
const loginWithPassword = vi.fn();

vi.mock('../../context/AuthContext', () => ({ useAuth: () => ({ sendOTP, verifyOTP, loginWithPassword }) }));
vi.mock('../../context/ToastContext', () => ({ useToast: () => ({ success: vi.fn(), error: vi.fn() }) }));
vi.mock('../../utils/seo', () => ({ usePageMeta: () => {} }));

const apiError = (status, data) => Object.assign(new Error('request failed'), { response: { status, data } });
const field = (id) => document.getElementById(id);
const type = (id, value) => fireEvent.change(field(id), { target: { value } });
const submit = (id) => fireEvent.submit(field(id).closest('form'));
const alertText = () => screen.getByRole('alert').textContent;

function renderPage(state) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: '/login', state }]}>
      <Login />
    </MemoryRouter>,
  );
}

describe('Login errors are shown in Persian, not as the API sentence', () => {
  beforeEach(() => {
    sendOTP.mockReset().mockResolvedValue({});
    verifyOTP.mockReset().mockResolvedValue({});
    loginWithPassword.mockReset().mockResolvedValue({});
  });

  it('wrong password, rate limit and a server problem', async () => {
    renderPage();
    const attempt = async (error, expected) => {
      loginWithPassword.mockRejectedValueOnce(error);
      type('identifier', '09121234567');
      type('password', 'some-password');
      submit('password');
      await waitFor(() => expect(alertText()).toBe(expected));
    };
    await attempt(
      apiError(400, { non_field_errors: ['Invalid username/phone or password.'], code: 'invalid_credentials' }),
      fa.auth.errInvalidCredentials,
    );
    await attempt(apiError(429, { detail: 'Request was throttled.' }), fa.auth.errTooMany);
    await attempt(apiError(500, '<h1>Server Error</h1>'), fa.auth.errGeneric);
    await attempt(new Error('Network Error'), fa.auth.errGeneric);
  });

  it('SMS login: unknown number and SMS failure', async () => {
    renderPage();
    fireEvent.click(screen.getAllByRole('tab')[1]);
    const attempt = async (error, expected) => {
      sendOTP.mockRejectedValueOnce(error);
      type('otp-phone', '09121234567');
      submit('otp-phone');
      await waitFor(() => expect(alertText()).toBe(expected));
    };
    await attempt(apiError(404, { error: 'No user found with this phone number.', code: 'user_not_found' }), fa.auth.errUserNotFound);
    await attempt(apiError(503, { error: 'Could not send the SMS.', code: 'sms_failed' }), fa.auth.errSmsFailed);
  });

  it('SMS login: a wrong code stays in the box, a dead code is cleared', async () => {
    renderPage();
    fireEvent.click(screen.getAllByRole('tab')[1]);
    type('otp-phone', '09121234567');
    submit('otp-phone');
    await waitFor(() => expect(field('otp-code')).toBeTruthy());

    verifyOTP.mockRejectedValueOnce(apiError(400, { error: 'Invalid OTP code.', code: 'otp_invalid' }));
    type('otp-code', '123456');
    submit('otp-code');
    await waitFor(() => expect(alertText()).toBe(fa.auth.errOtpInvalid));
    expect(field('otp-code').value).toBe('123456');

    verifyOTP.mockRejectedValueOnce(apiError(400, { error: 'OTP has expired.', code: 'otp_expired' }));
    submit('otp-code');
    await waitFor(() => expect(alertText()).toBe(fa.auth.errOtpExpired));
    expect(field('otp-code').value).toBe('');
  });

  it('starts with the phone number passed from the forgot-password page', () => {
    renderPage({ phone: '09121234567' });
    expect(field('identifier').value).toBe('09121234567');
  });
});
