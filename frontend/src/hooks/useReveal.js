import { useEffect } from 'react';

/**
 * Fade-and-rise for every [data-reveal] element inside `ref` as it scrolls into view.
 * Adds the class "in" once per element. Shows everything at once for reduced motion
 * or browsers without IntersectionObserver. Pass `deps` that change when new
 * [data-reveal] elements render (for example after data loads).
 */
export default function useReveal(ref, deps = []) {
  useEffect(() => {
    const root = ref.current;
    if (!root) return undefined;
    const items = root.querySelectorAll('[data-reveal]:not(.in)');
    if (!('IntersectionObserver' in window) || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      items.forEach((el) => el.classList.add('in'));
      return undefined;
    }
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          io.unobserve(e.target);
        }
      }),
      { rootMargin: '0px 0px -8% 0px' },
    );
    items.forEach((el) => io.observe(el));
    return () => io.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
