import { useEffect, useLayoutEffect } from 'react';
import { useLocation, useNavigationType } from 'react-router-dom';

// New pages start at the top; back/forward keeps the browser's own scroll position.
export function ScrollToTop() {
  const { pathname } = useLocation();
  const navType = useNavigationType();
  useLayoutEffect(() => {
    if (navType !== 'POP') window.scrollTo({ top: 0, left: 0, behavior: 'instant' });
  }, [pathname, navType]);
  return null;
}

// Shown while a page's code chunk loads: a slim bar under the header instead of a full-page spinner.
export function PageLoader() {
  return (
    <div className="page-loader" role="progressbar" aria-busy="true" aria-label="Loading">
      <span className="page-loader-bar" />
    </div>
  );
}

// Warm up the chunks shoppers usually open next, once the browser is idle.
export function usePrefetchPages(loaders) {
  useEffect(() => {
    const run = () => loaders.forEach((load) => load().catch(() => {}));
    if ('requestIdleCallback' in window) {
      const id = window.requestIdleCallback(run, { timeout: 4000 });
      return () => window.cancelIdleCallback(id);
    }
    const id = setTimeout(run, 2500);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}
