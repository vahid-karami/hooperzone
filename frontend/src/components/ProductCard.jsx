import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useFavorites } from '../context/FavoritesContext';
import { useAuth } from '../context/AuthContext';
import ProductQuickView from './ProductQuickView';
import Price from './Price';
import Icon from './Icon';
import { bodyPartLabel } from '../utils/bodyParts';

export default function ProductCard({ product }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const { isAuthenticated } = useAuth();
  const { toggleFavorite, isInFavorites } = useFavorites();
  const navigate = useNavigate();
  const [showQuickView, setShowQuickView] = useState(false);

  const price = Number(product.price);
  const effective = Number(product.effective_price);
  const hasDiscount = product.discount_price && effective < price;
  const discountPercent = hasDiscount ? Math.round(((price - effective) / price) * 100) : 0;
  const isFavorite = isInFavorites(product.id);
  const name = (lang === 'fa' && product.name_fa) || product.name_localized || product.name;
  const url = `/products/${product.slug}`;

  const handleFavoriteClick = async () => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    await toggleFavorite(product.id);
  };

  return (
    <>
      <article className={`product-card ${product.in_stock ? '' : 'is-out'}`}>
        <div className="product-card-media">
          <Link to={url} className="product-card-img" tabIndex={-1} aria-hidden="true">
            {product.primary_image ? (
              <img
                src={product.primary_image.thumbnail || product.primary_image.image}
                alt={product.primary_image.alt_text || name}
                loading="lazy"
                decoding="async"
                width="600"
                height="600"
              />
            ) : (
              <span className="img-fallback"><Icon name="box" size={40} strokeWidth={1.2} /></span>
            )}
          </Link>

          <div className="product-card-badges">
            {hasDiscount && <span className="badge-sale">{t('product.discountBadge', '{{percent}}٪ تخفیف', { percent: discountPercent })}</span>}
            {product.is_featured && <span className="badge-soft">{t('product.bestseller', 'پرفروش')}</span>}
          </div>

          <button
            type="button"
            onClick={handleFavoriteClick}
            className={`fav-btn ${isFavorite ? 'on' : ''}`}
            aria-pressed={isFavorite}
            aria-label={isFavorite ? t('product.removeFavorite', 'حذف از علاقه‌مندی‌ها') : t('product.addFavorite', 'افزودن به علاقه‌مندی‌ها')}
          >
            <Icon name="heart" size={20} filled={isFavorite} />
          </button>

          <button type="button" className="quick-view-btn" onClick={() => setShowQuickView(true)}>
            {t('product.quickView', 'مشاهده سریع')}
          </button>
        </div>

        <div className="product-card-body">
          {product.injury_type && product.injury_type !== 'general' && (
            <span className="product-card-meta">{bodyPartLabel(product.injury_type, lang)}</span>
          )}
          <h3 className="product-card-title">
            <Link to={url}>{name}</Link>
          </h3>
          <div className="product-card-price">
            <span className="price-now"><Price amount={effective} /></span>
            {hasDiscount && <span className="price-was"><Price amount={price} showSymbol={false} /></span>}
          </div>
          {!product.in_stock && <span className="stock-note">{t('common.outOfStock')}</span>}
        </div>
      </article>

      {showQuickView && <ProductQuickView slug={product.slug} onClose={() => setShowQuickView(false)} />}
    </>
  );
}
