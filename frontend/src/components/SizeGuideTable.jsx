import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import Icon from './Icon';
import { toPersianNumber } from '../hooks/useLanguage';

const pick = (lang, fa, en) => (lang === 'fa' ? fa || en : en || fa) || '';

// A size guide (راهنمای سایز): how to measure, an optional diagram and the measurement table.
// `highlight` marks a size row (e.g. the size the customer picked).
export function SizeGuideTable({ guide, highlight }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (v) => (lang === 'fa' ? toPersianNumber(v) : String(v));
  const how = pick(lang, guide.how_to_measure_fa, guide.how_to_measure_en);
  const unit = (u) => (u === 'cm' ? t('product.unitCm', 'سانتی‌متر') : u);

  return (
    <div className="size-guide">
      {(how || guide.image) && (
        <div className="size-guide-how">
          {guide.image && <img src={guide.image} alt={t('product.howToMeasure', 'نحوه اندازه‌گیری')} loading="lazy" />}
          {how && (
            <div>
              <h3>{t('product.howToMeasure', 'نحوه اندازه‌گیری')}</h3>
              {how.split('\n').filter(Boolean).map((line) => <p key={line}>{line}</p>)}
            </div>
          )}
        </div>
      )}
      <div className="size-table-wrap">
        <table className="size-table">
          <thead>
            <tr>
              <th scope="col">{t('product.size')}</th>
              {guide.columns.map((c, i) => (
                <th scope="col" key={i}>
                  {pick(lang, c.label_fa, c.label_en)}
                  {c.unit && <small> ({unit(c.unit)})</small>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {guide.rows.map((row) => (
              <tr key={row.size} className={highlight && row.size.toLowerCase() === highlight.toLowerCase() ? 'is-picked' : ''}>
                <th scope="row" dir="ltr">{row.size}</th>
                {row.values.map((v, i) => <td key={i} dir="ltr">{num(v)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function SizeGuideModal({ guide, highlight, onClose }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-lg" role="dialog" aria-modal="true" aria-labelledby="size-guide-title" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 id="size-guide-title">{pick(lang, guide.title_fa, guide.title_en) || t('product.sizeGuide')}</h2>
          <button onClick={onClose} className="icon-btn" aria-label={t('common.close', 'بستن')}>
            <Icon name="close" />
          </button>
        </div>
        <div className="modal-body">
          <SizeGuideTable guide={guide} highlight={highlight} />
        </div>
      </div>
    </div>
  );
}
