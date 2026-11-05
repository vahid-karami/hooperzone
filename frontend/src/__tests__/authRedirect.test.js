import { describe, expect, it } from 'vitest';
import { afterLoginPath, loginState } from '../utils/authRedirect';

describe('authRedirect', () => {
  it('remembers the current path and query', () => {
    expect(loginState({ pathname: '/products/knee', search: '?size=M' })).toEqual({ from: '/products/knee?size=M' });
  });

  it('returns to the remembered in-app page', () => {
    expect(afterLoginPath({ state: { from: '/checkout' } })).toBe('/checkout');
  });

  it('falls back to home for missing, external or auth-page targets', () => {
    expect(afterLoginPath({})).toBe('/');
    expect(afterLoginPath({ state: { from: 'https://evil.example' } })).toBe('/');
    expect(afterLoginPath({ state: { from: '//evil.example' } })).toBe('/');
    expect(afterLoginPath({ state: { from: '/login' } })).toBe('/');
    expect(afterLoginPath({ state: { from: '/register?x=1' } })).toBe('/');
  });
});
