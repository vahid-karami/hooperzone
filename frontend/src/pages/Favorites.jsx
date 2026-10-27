import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { usePageMeta } from '../utils/seo';
import { useFavorites } from '../context/FavoritesContext';
import ProductCard from '../components/ProductCard';

export default function Favorites() {
  const { t } = useTranslation();
  usePageMeta({ title: t('header.myFavorites'), noindex: true });
  const { favorites, removeFromFavorites, clearFavorites } = useFavorites();

  if (!favorites.items || favorites.items.length === 0) {
    return (
      <div className="favorites-page">
        <div className="container">
          <div className="empty-state">
            <span className="empty-state-icon">♡</span>
            <h3>{t('favorites.emptyFavorites')}</h3>
            <p>{t('favorites.emptyFavoritesDesc')}</p>
            <Link to="/products" className="btn btn-primary">{t('cart.browseProducts')}</Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="favorites-page">
      <div className="container">
        <div className="favorites-header">
          <h1>{t('favorites.myFavorites')}</h1>
          <button onClick={clearFavorites} className="btn btn-ghost btn-sm">
            {t('common.clearAll')}
          </button>
        </div>

        <div className="products-grid">
          {favorites.items.map((item) => (
            <div key={item.id} className="favorite-item">
              <ProductCard product={item.product} />
              <button
                onClick={() => removeFromFavorites(item.product.id)}
                className="remove-favorite-btn"
                aria-label={t('favorites.removeFromFavorites')}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
