import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import '../../i18n';
import fa from '../../i18n/locales/fa.json';
import ForgotPassword from '../ForgotPassword';

const sendOTP = vi.fn();
const resetPassword = vi.fn();

vi.mock('../../context/AuthContext', () => ({ useAuth: () => ({ sendOTP, resetPassword }) }));
vi.mock('../../context/ToastContext', () => ({ useToast: () => ({ success: vi.fn(), error: vi.fn() }) }));
vi.mock('../../utils/seo', () => ({ usePageMeta: () => {} }));

const apiError = (status, data) => Object.assign(new Error('request failed'), { response: { status, data } });

function LoginStub() {
  const { state } = useLocation();
  return <p data-testid="login">{JSON.stringify(state)}</p>;
}

function renderPage(state) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: '/forgot-password', state }]}>
      <Routes>
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/login" element={<LoginStub />} />
      </Routes>
    </MemoryRouter>,
  );
}

const field = (id) => document.getElementById(id);
const type = (id, value) => fireEvent.change(field(id), { target: { value } });
const submit = (id) => fireEvent.submit(field(id).closest('form'));

async function reachResetStep(phone = '09121234567') {
  type('forgot-phone', phone);
  submit('forgot-phone');
  await waitFor(() => expect(field('forgot-code')).toBeTruthy());
}

describe('ForgotPassword', () => {
  beforeEach(() => {
    sendOTP.mockReset().mockResolvedValue({});
    resetPassword.mockReset().mockResolvedValue({});
  });

  it('asks for a valid phone before sending anything', () => {
    renderPage();
    type('forgot-phone', '0912');
    submit('forgot-phone');
    expect(sendOTP).not.toHaveBeenCalled();
    expect(screen.getByRole('alert').textContent).toBe(fa.auth.invalidPhone);
  });

  it('requests a reset code, with Persian digits typed by the customer', async () => {
    renderPage();
    await reachResetStep('۰۹۱۲۱۲۳۴۵۶۷');
    expect(sendOTP).toHaveBeenCalledWith('09121234567', 'reset_password');
  });

  it('says so when no account has that phone', async () => {
    sendOTP.mockRejectedValue(apiError(404, { error: 'No user found with this phone number.', code: 'user_not_found' }));
    renderPage();
    type('forgot-phone', '09121234567');
    submit('forgot-phone');
    await waitFor(() => expect(screen.getByRole('alert').textContent).toBe(fa.auth.errUserNotFound));
    expect(field('forgot-code')).toBeNull();
  });

  it('checks the code, the password rules and the repeat before calling the server', async () => {
    renderPage();
    await reachResetStep();
    const attempt = (code, password, confirm = password) => {
      type('forgot-code', code);
      type('forgot-password', password);
      type('forgot-password-confirm', confirm);
      submit('forgot-code');
      return screen.getByRole('alert').textContent;
    };
    expect(attempt('123', 'blue-Kettle-41')).toBe(fa.auth.invalidCode);
    expect(attempt('123456', '12345678')).toBe(fa.auth.passwordAllDigits);
    expect(attempt('123456', 'short1')).toBe(fa.auth.passwordTooShort);
    expect(attempt('123456', 'blue-Kettle-41', 'blue-Kettle-42')).toBe(fa.auth.passwordMismatch);
    expect(resetPassword).not.toHaveBeenCalled();
  });

  it('saves the new password and returns to login with the phone and the page to go back to', async () => {
    renderPage({ from: '/checkout' });
    await reachResetStep();
    type('forgot-code', '۱۲۳۴۵۶');
    type('forgot-password', 'blue-Kettle-41');
    type('forgot-password-confirm', 'blue-Kettle-41');
    submit('forgot-code');
    await waitFor(() => expect(screen.getByTestId('login')).toBeTruthy());
    expect(resetPassword).toHaveBeenCalledWith('09121234567', '123456', 'blue-Kettle-41');
    expect(JSON.parse(screen.getByTestId('login').textContent)).toEqual({ from: '/checkout', phone: '09121234567' });
  });

  it('shows server errors in Persian and clears a code that can no longer work', async () => {
    renderPage();
    await reachResetStep();
    const send = async (response, expected) => {
      resetPassword.mockRejectedValueOnce(response);
      type('forgot-code', '123456');
      type('forgot-password', 'blue-Kettle-41');
      type('forgot-password-confirm', 'blue-Kettle-41');
      submit('forgot-code');
      await waitFor(() => expect(screen.getByRole('alert').textContent).toBe(expected));
    };
    await send(apiError(400, { error: 'Invalid OTP code.', code: 'otp_invalid' }), fa.auth.errOtpInvalid);
    expect(field('forgot-code').value).toBe('123456');
    await send(apiError(400, { password: ['x'], password_codes: ['password_too_common'] }), fa.auth.passwordTooCommon);
    await send(apiError(400, { error: 'Too many wrong codes.', code: 'otp_locked' }), fa.auth.errOtpLocked);
    expect(field('forgot-code').value).toBe('');
  });

  it('offers to send the code again only after the wait', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      renderPage();
      await reachResetStep();
      const resend = () => screen.getAllByRole('button').find((b) => b.className === 'auth-link-btn');
      expect(resend().disabled).toBe(true);
      // One tick per second: each one re-renders and schedules the next.
      for (let second = 0; second < 60; second += 1) {
        await act(async () => {
          await vi.advanceTimersByTimeAsync(1000);
        });
      }
      await waitFor(() => expect(resend().disabled).toBe(false));
      expect(resend().textContent).toBe(fa.auth.resendCode);
      fireEvent.click(resend());
      await waitFor(() => expect(sendOTP).toHaveBeenCalledTimes(2));
    } finally {
      vi.useRealTimers();
    }
  });
});
