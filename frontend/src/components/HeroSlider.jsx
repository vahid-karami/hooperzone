import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Icon from './Icon';

const AUTOPLAY_MS = 6000;

/**
 * Slogan carousel for the top of the home page.
 * slides: [{ key, eyebrow, title, text, cta: { label, to | href, icon }, image, theme }]
 * Autoplays (paused on hover, focus, touch, hidden tab and for reduced motion); swipe, arrows and dots.
 */
export default function HeroSlider({ slides }) {
  const { t, i18n } = useTranslation();
  const rtl = i18n.dir() === 'rtl';
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const touchX = useRef(null);
  const count = slides.length;

  const go = useCallback((i) => setIndex(((i % count) + count) % count), [count]);

  useEffect(() => {
    if (paused || count < 2) return undefined;
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined;
    const id = setInterval(() => {
      if (!document.hidden) setIndex((i) => (i + 1) % count);
    }, AUTOPLAY_MS);
    return () => clearInterval(id);
  }, [paused, count, index]);

  if (!count) return null;

  const onTouchStart = (e) => {
    touchX.current = e.touches[0].clientX;
    setPaused(true);
  };
  const onTouchEnd = (e) => {
    if (touchX.current == null) return;
    const dx = e.changedTouches[0].clientX - touchX.current;
    touchX.current = null;
    setPaused(false);
    if (Math.abs(dx) < 40) return;
    // In RTL the next slide sits to the left, so dragging right reveals it.
    const forward = rtl ? dx > 0 : dx < 0;
    go(index + (forward ? 1 : -1));
  };

  return (
    <section
      className={`hero-slider ${paused ? 'is-paused' : ''}`}
      aria-roledescription="carousel"
      aria-label={t('home.sliderLabel', 'شعارهای هوپرزون')}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <div className="hero-slider-viewport" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
        <div
          className="hero-slider-track"
          style={{ transform: `translateX(${(rtl ? 1 : -1) * index * 100}%)` }}
        >
          {slides.map((s, i) => {
            const active = i === index;
            const cta = s.cta;
            const ctaInner = (
              <>
                {cta?.icon && <Icon name={cta.icon} size={18} />} {cta?.label}
              </>
            );
            return (
              <div
                key={s.key}
                className={`hero-slide theme-${s.theme || 'photo'} ${active ? 'is-active' : ''}`}
                role="group"
                aria-roledescription="slide"
                aria-label={`${i + 1} / ${count}`}
                aria-hidden={!active}
                inert={!active}
              >
                {s.image && (
                  <img
                    src={s.image}
                    srcSet={s.srcSet}
                    sizes={s.srcSet ? '(max-width: 1240px) 100vw, 1200px' : undefined}
                    alt=""
                    decoding="async"
                    fetchPriority={i === 0 ? 'high' : 'auto'}
                    loading={i === 0 ? 'eager' : 'lazy'}
                  />
                )}
                <span className="hero-slide-shape" aria-hidden="true" />
                <span className="hero-slide-glow" aria-hidden="true" />
                <div className="hero-slide-content">
                  {s.eyebrow && <span className="hero-slide-eyebrow">{s.eyebrow}</span>}
                  {i === 0 ? <h1>{s.title}</h1> : <h2>{s.title}</h2>}
                  {s.text && <p>{s.text}</p>}
                  {cta &&
                    (cta.to ? (
                      <Link to={cta.to} className="btn btn-lg hero-slide-cta">{ctaInner}</Link>
                    ) : (
                      <a href={cta.href} className="btn btn-lg hero-slide-cta">{ctaInner}</a>
                    ))}
                </div>
              </div>
            );
          })}
        </div>

        {count > 1 && (
          <>
            <button
              type="button"
              className="hero-slider-arrow is-prev"
              onClick={() => go(index - 1)}
              aria-label={t('home.sliderPrev', 'تصویر قبلی')}
            >
              <Icon name={rtl ? 'chevronRight' : 'chevronLeft'} />
            </button>
            <button
              type="button"
              className="hero-slider-arrow is-next"
              onClick={() => go(index + 1)}
              aria-label={t('home.sliderNext', 'تصویر بعدی')}
            >
              <Icon name={rtl ? 'chevronLeft' : 'chevronRight'} />
            </button>
          </>
        )}
      </div>

      {count > 1 && (
        <div className="hero-slider-dots">
          {slides.map((s, i) => (
            <button
              key={s.key}
              type="button"
              className={i === index ? 'is-active' : ''}
              onClick={() => go(i)}
              aria-label={t('home.sliderGoTo', { n: i + 1, defaultValue: 'تصویر {{n}}' })}
              aria-current={i === index}
            />
          ))}
        </div>
      )}
    </section>
  );
}
