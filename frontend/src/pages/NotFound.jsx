import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import Icon from '../components/Icon';
import { usePageMeta } from '../utils/seo';

export default function NotFound() {
  const { t } = useTranslation();
  usePageMeta({ title: t('notFound.title'), noindex: true });

  return (
    <div className="container">
      <div className="empty-panel not-found">
        <span className="not-found-code" aria-hidden="true">404</span>
        <Icon name="search" size={40} strokeWidth={1.4} />
        <h1>{t('notFound.title')}</h1>
        <p>{t('notFound.text')}</p>
        <div className="empty-actions">
          <Link to="/" className="btn btn-primary">{t('notFound.home')}</Link>
          <Link to="/products" className="btn btn-outline">{t('notFound.shop')}</Link>
        </div>
      </div>
    </div>
  );
}
