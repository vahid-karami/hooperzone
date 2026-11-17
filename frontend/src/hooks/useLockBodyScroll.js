import { useEffect } from 'react';

// How many open modals asked for the lock: the page scrolls again only when the last one closes.
let locks = 0;
let savedOverflow = '';
let savedPadding = '';

/**
 * Stops the page behind a modal from scrolling while the modal is open.
 * Without it, a swipe inside a modal on a phone also moves the page underneath.
 */
export default function useLockBodyScroll(active = true) {
  useEffect(() => {
    if (!active) return undefined;
    const { body, documentElement } = document;
    if (locks === 0) {
      savedOverflow = body.style.overflow;
      savedPadding = body.style.paddingInlineEnd;
      // Desktop: keep the layout from jumping sideways when the scrollbar disappears.
      const scrollbar = window.innerWidth - documentElement.clientWidth;
      if (scrollbar > 0) body.style.paddingInlineEnd = `${scrollbar}px`;
      body.style.overflow = 'hidden';
    }
    locks += 1;
    return () => {
      locks -= 1;
      if (locks === 0) {
        body.style.overflow = savedOverflow;
        body.style.paddingInlineEnd = savedPadding;
      }
    };
  }, [active]);
}
