import { useTranslation } from 'react-i18next';
import Icon from '../Icon';
import { toPersianNumber } from '../../hooks/useLanguage';

// Prev/next pager for paginated admin lists ({count, next, previous} from DRF).
export default function AdminPager({ page, pageSize, count, onChange }) {
  const { t, i18n } = useTranslation();
  const num = (n) => (i18n.language === 'fa' ? toPersianNumber(n) : String(n));
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (count <= pageSize) return null;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, count);

  return (
    <nav className="admin-pager" aria-label={t('products.pagination', 'صفحه‌بندی')}>
      <span className="muted">
        {t('admin.pagerRange', '{{from}}–{{to}} از {{count}}', { from: num(from), to: num(to), count: num(count) })}
      </span>
      <div className="admin-pager-btns">
        <button className="page-btn" disabled={page <= 1} onClick={() => onChange(page - 1)} aria-label={t('admin.prevPage', 'صفحه قبل')}>
          <Icon name="chevronRight" size={18} className="flip-ltr" />
        </button>
        <span className="admin-pager-current">{num(page)} / {num(pages)}</span>
        <button className="page-btn" disabled={page >= pages} onClick={() => onChange(page + 1)} aria-label={t('admin.nextPage', 'صفحه بعد')}>
          <Icon name="chevronLeft" size={18} className="flip-ltr" />
        </button>
      </div>
    </nav>
  );
}
