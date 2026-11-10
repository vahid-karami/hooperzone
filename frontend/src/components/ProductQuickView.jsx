import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import Price from './Price';
import Icon from './Icon';
import { loginState } from '../utils/authRedirect';

export default function ProductQuickView({ slug, onClose }) {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const { addToCart } = useCart();
  const { isAuthenticated } = useAuth();
  const { success, error: showError } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [sizeId, setSizeId] = useState(null);

  useEffect(() => {
    apiClient
      .get(ENDPOINTS.productDetail(slug))
      .then((response) => {
        setProduct(response.data);
        const sizes = response.data.sizes || [];
        if (sizes.length === 1 && sizes[0].in_stock) setSizeId(sizes[0].id);
      })
      .catch((error) => console.error('Failed to fetch product:', error))
      .finally(() => setLoading(false));
  }, [slug]);

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  const handleAddToCart = async () => {
    if (!isAuthenticated) {
      navigate('/login', { state: loginState(location) });
      return;
    }
    if (product.sizes?.length && !sizeId) {
      showError(t('product.chooseSize', 'لطفاً سایز را انتخاب کنید'));
      return;
    }
    setAdding(true);
    try {
      await addToCart(product.id, 1, sizeId);
      success(t('cart.addedToCart'));
      onClose();
    } catch (err) {
      showError(err.response?.data?.error || t('cart.addFailed'));
    } finally {
      setAdding(false);
    }
  };

  const name = product ? (lang === 'fa' && product.name_fa) || product.name_localized || product.name : '';
  const description = product
    ? (lang === 'fa' && product.description_fa) || product.description_localized || product.description
    : '';
  const hasDiscount = product && product.discount_price && Number(product.effective_price) < Number(product.price);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal modal-lg" role="dialog" aria-modal="true" aria-label={name || t('product.quickView', 'مشاهده سریع')} onClick={(e) => e.stopPropagation()}>
        <button onClick={onClose} className="icon-btn modal-x" aria-label={t('common.close', 'بستن')}>
          <Icon name="close" />
        </button>
        {loading ? (
          <div className="loading"><div className="spinner" /></div>
        ) : product ? (
          <div className="quick-view">
            <div className="quick-view-img">
              {product.images?.length ? <img src={product.images[0].thumbnail || product.images[0].image} alt={name} decoding="async" /> : <Icon name="box" size={56} strokeWidth={1.2} />}
            </div>
            <div className="quick-view-info">
              {product.brand && <span className="eyebrow">{product.brand}</span>}
              <h2>{name}</h2>
              <div className="pdp-price">
                <span className="price-now"><Price amount={product.effective_price} /></span>
                {hasDiscount && <span className="price-was"><Price amount={product.price} showSymbol={false} /></span>}
              </div>
              {/* A preview: the first paragraph only; the product page has the rest. */}
              {description && <p className="quick-view-desc">{description.split(/\n\s*\n/)[0]}</p>}
              <span className={`stock-pill ${product.in_stock ? 'ok' : 'out'}`}>
                <span className="dot" />
                {product.in_stock ? t('product.available', 'موجود') : t('common.outOfStock')}
              </span>
              {product.in_stock && product.sizes?.length > 0 && (
                <div className="pdp-option">
                  <div className="pdp-option-head"><span id="qv-size-label">{t('product.size')}</span></div>
                  <div className="size-chips" role="radiogroup" aria-labelledby="qv-size-label">
                    {product.sizes.map((s) => (
                      <button
                        key={s.id}
                        type="button"
                        role="radio"
                        aria-checked={s.id === sizeId}
                        disabled={!s.in_stock}
                        className={`chip size-chip ${s.id === sizeId ? 'active' : ''}`}
                        onClick={() => setSizeId(s.id)}
                        dir="ltr"
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <div className="quick-view-actions">
                {product.in_stock && (
                  <button onClick={handleAddToCart} disabled={adding} className="btn btn-primary btn-lg">
                    <Icon name="bag" size={20} /> {adding ? t('common.loading') : t('common.addToCart')}
                  </button>
                )}
                <Link to={`/products/${product.slug}`} className="btn btn-outline btn-lg" onClick={onClose}>
                  {t('product.viewDetails', 'مشاهده جزئیات')}
                </Link>
              </div>
            </div>
          </div>
        ) : (
          <p className="muted">{t('product.notFound')}</p>
        )}
      </div>
    </div>
  );
}
