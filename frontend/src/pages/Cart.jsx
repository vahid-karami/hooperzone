import { Link, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { CartSkeleton } from '../components/Skeletons';
import Price from '../components/Price';
import Icon from '../components/Icon';
import Breadcrumbs from '../components/Breadcrumbs';
import { bodyPartLabel } from '../utils/bodyParts';
import { toPersianNumber } from '../hooks/useLanguage';
import { usePageMeta } from '../utils/seo';

export default function Cart() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const { cart, updateCartItem, removeFromCart, clearCart, loading: cartLoading } = useCart();
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const { info, error: showError } = useToast();

  usePageMeta({ title: t('cart.shoppingCart'), noindex: true });

  const itemName = (product) => (lang === 'fa' && product.name_fa) || product.name_localized || product.name;

  const handleQuantity = async (item, quantity) => {
    try {
      await updateCartItem(item.id, quantity);
    } catch (err) {
      showError(err.response?.data?.error || t('cart.updateFailed', 'به‌روزرسانی سبد انجام نشد'));
    }
  };

  const handleRemove = async (item) => {
    try {
      await removeFromCart(item.id);
      info(t('cart.itemRemoved', '«{{name}}» از سبد حذف شد', { name: itemName(item.product) }));
    } catch {
      showError(t('cart.updateFailed', 'به‌روزرسانی سبد انجام نشد'));
    }
  };

  const handleClear = async () => {
    if (!window.confirm(t('cart.clearConfirm', 'همه کالاها از سبد حذف شوند؟'))) return;
    await clearCart();
    info(t('cart.cleared', 'سبد خرید خالی شد'));
  };

  const crumbs = [
    { to: '/', label: t('common.home') },
    { label: t('cart.shoppingCart') },
  ];

  const emptyState = (title, text, action) => (
    <div className="container">
      <Breadcrumbs items={crumbs} />
      <div className="empty-panel">
        <Icon name="bag" size={44} strokeWidth={1.4} />
        <h2>{title}</h2>
        <p>{text}</p>
        <div className="empty-actions">{action}</div>
      </div>
    </div>
  );

  if (!isAuthenticated) {
    return emptyState(
      t('cart.emptyCart'),
      t('cart.addToCartFirst'),
      <Link to="/login" className="btn btn-primary">{t('common.signIn')}</Link>,
    );
  }

  if (cartLoading && cart.id === undefined) {
    return (
      <div className="container">
        <CartSkeleton />
      </div>
    );
  }

  if (!cart.items || cart.items.length === 0) {
    return emptyState(
      t('cart.emptyCart'),
      t('cart.emptyCartDesc'),
      <Link to="/products" className="btn btn-primary">{t('cart.browseProducts')}</Link>,
    );
  }

  const subtotal = Number(cart.total_price) || 0;
  const savings = cart.items.reduce(
    (sum, item) => sum + Math.max(0, Number(item.product.price) - Number(item.product.effective_price)) * item.quantity,
    0,
  );

  return (
    <div className="cart-page">
      <div className="container">
        <Breadcrumbs items={crumbs} />
        <div className="page-title-row">
          <h1 className="display-title">{t('cart.shoppingCart')}</h1>
          <span className="page-title-meta">{t('cart.itemsCount', '{{count}} کالا', { count: num(cart.total_items) })}</span>
        </div>

        <div className="cart-layout">
          <div className="cart-items">
            <ul className="cart-list">
              {cart.items.map((item) => {
                const product = item.product;
                const hasDiscount = Number(product.effective_price) < Number(product.price);
                return (
                  <li key={item.id} className="cart-row">
                    <Link to={`/products/${product.slug}`} className="cart-row-img" tabIndex={-1} aria-hidden="true">
                      {product.primary_image ? (
                        <img src={product.primary_image.thumbnail || product.primary_image.image} alt="" loading="lazy" decoding="async" />
                      ) : (
                        <Icon name="box" size={32} strokeWidth={1.2} />
                      )}
                    </Link>

                    <div className="cart-row-info">
                      {product.injury_type && product.injury_type !== 'general' && (
                        <span className="product-card-meta">{bodyPartLabel(product.injury_type, lang)}</span>
                      )}
                      <h2 className="cart-row-title">
                        <Link to={`/products/${product.slug}`}>{itemName(product)}</Link>
                      </h2>
                      <div className="cart-row-unit">
                        <Price amount={product.effective_price} />
                        {hasDiscount && <span className="price-was"><Price amount={product.price} showSymbol={false} /></span>}
                      </div>
                    </div>

                    <div className="qty cart-row-qty" role="group" aria-label={t('cart.quantity', 'تعداد')}>
                      <button onClick={() => handleQuantity(item, item.quantity + 1)} aria-label={t('product.increase', 'افزایش')}>
                        <Icon name="plus" size={16} />
                      </button>
                      <span aria-live="polite">{num(item.quantity)}</span>
                      <button
                        onClick={() => handleQuantity(item, item.quantity - 1)}
                        disabled={item.quantity <= 1}
                        aria-label={t('product.decrease', 'کاهش')}
                      >
                        <Icon name="minus" size={16} />
                      </button>
                    </div>

                    <div className="cart-row-total">
                      <Price amount={item.subtotal} />
                    </div>

                    <button className="icon-btn cart-row-remove" onClick={() => handleRemove(item)} aria-label={t('cart.remove', 'حذف')}>
                      <Icon name="close" size={18} />
                    </button>
                  </li>
                );
              })}
            </ul>

            <div className="cart-actions">
              <Link to="/products" className="link-arrow">
                <Icon name="chevronRight" size={16} className="flip-ltr" /> {t('common.continueShopping')}
              </Link>
              <button onClick={handleClear} className="clear-link">{t('cart.clearCart')}</button>
            </div>
          </div>

          <aside className="summary-card">
            <h2>{t('cart.orderSummary')}</h2>
            <dl className="summary-rows">
              <div>
                <dt>{t('cart.subtotal')}</dt>
                <dd><Price amount={subtotal} /></dd>
              </div>
              {savings > 0 && (
                <div className="summary-savings">
                  <dt>{t('cart.yourSavings', 'سود شما از خرید')}</dt>
                  <dd><Price amount={savings} /></dd>
                </div>
              )}
              <div>
                <dt>{t('cart.shipping')}</dt>
                <dd className="summary-muted">{t('cart.shippingAtCheckout', 'در مرحله بعد')}</dd>
              </div>
              <div className="summary-total">
                <dt>{t('cart.total')}</dt>
                <dd><Price amount={subtotal} /></dd>
              </div>
            </dl>

            <button onClick={() => navigate('/checkout')} className="btn btn-energy btn-lg btn-full">
              {t('cart.proceedToCheckout')}
            </button>

            <ul className="summary-perks">
              <li><Icon name="shield" size={18} /> {t('cart.secureCheckout')}</li>
              <li><Icon name="truck" size={18} /> {t('cart.fastDelivery')}</li>
              <li><Icon name="returns" size={18} /> {t('home.trustReturnText', '۷ روز ضمانت بازگشت کالا')}</li>
            </ul>
          </aside>
        </div>
      </div>
    </div>
  );
}
