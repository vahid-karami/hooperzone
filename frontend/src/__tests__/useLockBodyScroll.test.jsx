import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import useLockBodyScroll from '../hooks/useLockBodyScroll';

function Modal({ active = true }) {
  useLockBodyScroll(active);
  return null;
}

describe('useLockBodyScroll', () => {
  it('stops the page scrolling while mounted and restores it after', () => {
    document.body.style.overflow = 'auto';
    const { unmount } = render(<Modal />);
    expect(document.body.style.overflow).toBe('hidden');
    unmount();
    expect(document.body.style.overflow).toBe('auto');
    document.body.style.overflow = '';
  });

  it('keeps the lock until the last of several modals closes', () => {
    const first = render(<Modal />);
    const second = render(<Modal />);
    first.unmount();
    expect(document.body.style.overflow).toBe('hidden');
    second.unmount();
    expect(document.body.style.overflow).toBe('');
  });

  it('does nothing while inactive', () => {
    const { rerender, unmount } = render(<Modal active={false} />);
    expect(document.body.style.overflow).toBe('');
    rerender(<Modal active />);
    expect(document.body.style.overflow).toBe('hidden');
    unmount();
    expect(document.body.style.overflow).toBe('');
  });
});
