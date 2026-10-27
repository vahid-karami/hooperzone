import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import apiClient from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import { useCart } from '../context/CartContext';
import { useAuth } from '../context/AuthContext';
import { useFavorites } from '../context/FavoritesContext';
import { useToast } from '../context/ToastContext';
import { ProductDetailSkeleton } from '../components/Skeletons';
import { usePageMeta, ProductSchema, BreadcrumbSchema } from '../utils/seo';
import Price from '../components/Price';
import Icon from '../components/Icon';
import Breadcrumbs from '../components/Breadcrumbs';
import ProductCard from '../components/ProductCard';
import { bodyPartLabel } from '../utils/bodyParts';
import { toPersianNumber } from '../hooks/useLanguage';
import { formatDate } from '../utils/persianDate';

function Stars({ value, size = 16 }) {
  return (
    <span className="stars" aria-hidden="true">
      {[1, 2, 3, 4, 5].map((i) => (
        <Icon key={i} name="star" size={size} filled={i <= Math.round(value)} strokeWidth={1.4} />
      ))}
    </span>
  );
}

function Accordion({ id, title, open, onToggle, children }) {
  return (
    <section className={`accordion ${open ? 'open' : ''}`} id={id}>
      <h2>
        <button type="button" aria-expanded={open} aria-controls={`${id}-panel`} onClick={onToggle}>
          {title}
          <Icon name="chevronDown" size={20} />
        </button>
      </h2>
      <div className="accordion-panel" id={`${id}-panel`} hidden={!open}>
        {children}
      </div>
    </section>
  );
}

export default function ProductDetail() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const num = (n) => (lang === 'fa' ? toPersianNumber(n) : String(n));
  const { slug } = useParams();
  const navigate = useNavigate();
  const { addToCart } = useCart();
  const { isAuthenticated, user } = useAuth();
  const { toggleFavorite, isInFavorites } = useFavorites();
  const { success, error: showError } = useToast();

  const [product, setProduct] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [related, setRelated] = useState([]);
  const [quantity, setQuantity] = useState(1);
  const [loading, setLoading] = useState(true);
  const [addingToCart, setAddingToCart] = useState(false);
  const [activeImage, setActiveImage] = useState(0);
  const [openSection, setOpenSection] = useState({ about: true, specs: false, reviews: false });
  const [showSizeGuide, setShowSizeGuide] = useState(false);
  const [reviewForm, setReviewForm] = useState({ rating: 5, title: '', comment: '' });
  const [submittingReview, setSubmittingReview] = useState(false);

  const name = product ? (lang === 'fa' && product.name_fa) || product.name_localized || product.name : '';
  const description = product
    ? (lang === 'fa' && product.description_fa) || product.description_localized || product.description
    : '';

  usePageMeta({
    title: (lang === 'fa' && product?.meta_title) || name,
    description: ((lang === 'fa' && product?.meta_description) || description).slice(0, 170),
    image: product?.images?.[0]?.image,
    type: 'product',
  });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setActiveImage(0);
    setQuantity(1);
    Promise.all([apiClient.get(ENDPOINTS.productDetail(slug)), apiClient.get(ENDPOINTS.productReviews(slug))])
      .then(([productRes, reviewsRes]) => {
        if (cancelled) return;
        setProduct(productRes.data);
        setReviews(reviewsRes.data);
        return apiClient.get(ENDPOINTS.products, { params: { injury_type: productRes.data.injury_type } });
      })
      .then((relatedRes) => {
        if (cancelled || !relatedRes) return;
        const items = (relatedRes.data.results || relatedRes.data).filter((p) => p.slug !== slug);
        setRelated(items.slice(0, 4));
      })
      .catch((error) => {
        if (!cancelled) console.error('Failed to fetch product:', error);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const handleAddToCart = async () => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    setAddingToCart(true);
    try {
      await addToCart(product.id, quantity);
      success(t('cart.addedToCart'));
    } catch (err) {
      showError(err.response?.data?.error || t('cart.addFailed'));
    } finally {
      setAddingToCart(false);
    }
  };

  const handleFavorite = async () => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    await toggleFavorite(product.id);
  };

  const handleSubmitReview = async (e) => {
    e.preventDefault();
    setSubmittingReview(true);
    try {
      await apiClient.post(ENDPOINTS.reviewCreate(slug), reviewForm);
      const reviewsRes = await apiClient.get(ENDPOINTS.productReviews(slug));
      setReviews(reviewsRes.data);
      setReviewForm({ rating: 5, title: '', comment: '' });
      success(t('product.reviewSubmitted', 'نظر شما ثبت شد.'));
    } catch (error) {
      showError(error.response?.data?.error || t('product.reviewFailed'));
    } finally {
      setSubmittingReview(false);
    }
  };

  const openReviews = () => {
    setOpenSection((s) => ({ ...s, reviews: true }));
    requestAnimationFrame(() => document.getElementById('reviews')?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  };

  if (loading) {
    return (
      <div className="container">
        <ProductDetailSkeleton />
      </div>
    );
  }

  if (!product) {
    return (
      <div className="container">
        <div className="empty-panel">
          <Icon name="box" size={40} strokeWidth={1.4} />
          <h2>{t('product.notFound')}</h2>
          <Link to="/products" className="btn btn-primary">{t('cart.browseProducts')}</Link>
        </div>
      </div>
    );
  }

  const images = product.images || [];
  const price = Number(product.price);
  const effective = Number(product.effective_price);
  const hasDiscount = product.discount_price && effective < price;
  const discountPercent = hasDiscount ? Math.round(((price - effective) / price) * 100) : 0;
  const avgRating = reviews.length ? reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length : 0;
  const isFavorite = isInFavorites(product.id);
  const alreadyReviewed = user && reviews.some((r) => r.user?.id === user.id);
  const categoryName = (lang === 'fa' && product.category?.name_fa) || product.category?.name;

  const specs = [
    { label: t('product.category'), value: categoryName },
    { label: t('products.bodyPart'), value: product.injury_type ? bodyPartLabel(product.injury_type, lang) : '' },
    { label: t('product.brand', 'برند'), value: product.brand },
    { label: t('product.size'), value: product.size },
    { label: t('product.color'), value: product.color },
    { label: t('product.material'), value: product.material },
    { label: t('product.weight'), value: product.weight ? `${num(Number(product.weight))} ${t('product.grams', 'گرم')}` : '' },
    { label: t('product.sku', 'کد محصول'), value: num(String(product.id).padStart(6, '0')) },
  ].filter((s) => s.value);

  const highlights = [
    product.material && t('product.highlightMaterial', 'جنس: {{material}}', { material: product.material }),
    product.size && t('product.highlightSize', 'سایز موجود: {{size}}', { size: product.size }),
    t('product.highlightShipping', 'ارسال سریع با پست و تیپاکس و ۷ روز ضمانت بازگشت'),
  ].filter(Boolean);

  const crumbs = [
    { to: '/', label: t('common.home') },
    { to: '/products', label: t('common.shop') },
    product.injury_type && product.injury_type !== 'general'
      ? { to: `/products?injury_type=${product.injury_type}`, label: bodyPartLabel(product.injury_type, lang) }
      : null,
    { label: name },
  ].filter(Boolean);

  return (
    <div className="pdp">
      <ProductSchema product={product} />
      <BreadcrumbSchema items={crumbs} />
      <div className="container">
        <Breadcrumbs items={crumbs} />

        <div className="pdp-main">
          <div className="pdp-gallery">
            {images.length > 1 && (
              <div className="pdp-thumbs" role="tablist" aria-label={t('product.images', 'تصاویر محصول')}>
                {images.map((img, idx) => (
                  <button
                    key={img.id}
                    role="tab"
                    aria-selected={idx === activeImage}
                    onClick={() => setActiveImage(idx)}
                    className={idx === activeImage ? 'active' : ''}
                  >
                    <img src={img.thumbnail || img.image} alt="" loading="lazy" decoding="async" width="96" height="96" />
                  </button>
                ))}
              </div>
            )}
            <div className="pdp-stage">
              {images.length ? (
                <img
                  src={images[activeImage]?.image || images[0].image}
                  alt={images[activeImage]?.alt_text || name}
                  fetchPriority={activeImage === 0 ? 'high' : 'auto'}
                  decoding="async"
                />
              ) : (
                <Icon name="box" size={64} strokeWidth={1.2} />
              )}
              {hasDiscount && (
                <span className="badge-sale pdp-badge">{t('product.discountBadge', '{{percent}}٪ تخفیف', { percent: num(discountPercent) })}</span>
              )}
              {images.length > 1 && (
                <>
                  <button className="stage-arrow prev" onClick={() => setActiveImage((i) => (i - 1 + images.length) % images.length)} aria-label={t('home.prevSlide', 'قبلی')}>
                    <Icon name="chevronRight" className="flip-ltr" />
                  </button>
                  <button className="stage-arrow next" onClick={() => setActiveImage((i) => (i + 1) % images.length)} aria-label={t('home.nextSlide', 'بعدی')}>
                    <Icon name="chevronLeft" className="flip-ltr" />
                  </button>
                </>
              )}
            </div>
          </div>

          <div className="pdp-info">
            {product.brand && <span className="eyebrow">{product.brand}</span>}
            <h1 className="pdp-title">{name}</h1>

            <button type="button" className="pdp-rating" onClick={openReviews}>
              <Stars value={avgRating} />
              <span>
                {reviews.length
                  ? t('product.ratingSummary', '{{rating}} از ۵ · {{count}} نظر', { rating: num(avgRating.toFixed(1)), count: num(reviews.length) })
                  : t('product.beFirstReview', 'اولین نظر را ثبت کنید')}
              </span>
            </button>

            <p className="pdp-lead">{description}</p>

            {product.sports?.length > 0 && (
              <div className="pdp-sports">
                <span>{t('product.suitableFor', 'مناسب برای')}:</span>
                {product.sports.map((s) => (
                  <Link key={s.slug} to={`/products?sport=${s.slug}`} className="chip">
                    {(lang === 'fa' && s.name_fa) || s.name}
                  </Link>
                ))}
              </div>
            )}

            <ul className="pdp-highlights">
              {highlights.map((h) => (
                <li key={h}><Icon name="checkCircle" size={20} /> {h}</li>
              ))}
            </ul>

            <div className="pdp-buybox">
              <div className="pdp-price">
                <span className="price-now"><Price amount={effective} /></span>
                {hasDiscount && <span className="price-was"><Price amount={price} showSymbol={false} /></span>}
              </div>

              <span className={`stock-pill ${product.in_stock ? 'ok' : 'out'}`}>
                <span className="dot" />
                {product.in_stock ? t('product.available', 'موجود') : t('common.outOfStock')}
              </span>

              {product.size && (
                <div className="pdp-option">
                  <div className="pdp-option-head">
                    <span>{t('product.size')}</span>
                    <button type="button" className="text-btn" onClick={() => setShowSizeGuide(true)}>
                      <Icon name="ruler" size={16} /> {t('product.sizeGuide')}
                    </button>
                  </div>
                  <div className="size-chips">
                    <span className="chip active">{product.size}</span>
                  </div>
                </div>
              )}

              {product.in_stock && (
                <div className="pdp-actions">
                  <div className="qty" role="group" aria-label={t('cart.quantity', 'تعداد')}>
                    <button onClick={() => setQuantity((q) => Math.min(product.stock, q + 1))} aria-label={t('product.increase', 'افزایش')} disabled={quantity >= product.stock}>
                      <Icon name="plus" size={18} />
                    </button>
                    <span aria-live="polite">{num(quantity)}</span>
                    <button onClick={() => setQuantity((q) => Math.max(1, q - 1))} aria-label={t('product.decrease', 'کاهش')} disabled={quantity <= 1}>
                      <Icon name="minus" size={18} />
                    </button>
                  </div>
                  <button onClick={handleAddToCart} disabled={addingToCart} className="btn btn-primary btn-lg pdp-add">
                    <Icon name="bag" size={20} />
                    {addingToCart ? t('common.loading') : t('common.addToCart')}
                  </button>
                  <button
                    type="button"
                    className={`pdp-fav ${isFavorite ? 'on' : ''}`}
                    onClick={handleFavorite}
                    aria-pressed={isFavorite}
                    aria-label={isFavorite ? t('product.removeFavorite', 'حذف از علاقه‌مندی‌ها') : t('product.addFavorite', 'افزودن به علاقه‌مندی‌ها')}
                  >
                    <Icon name="heart" size={22} filled={isFavorite} />
                  </button>
                </div>
              )}
            </div>

            <dl className="pdp-meta">
              <div><dt>{t('product.sku', 'کد محصول')}:</dt><dd>{num(String(product.id).padStart(6, '0'))}</dd></div>
              {categoryName && (
                <div>
                  <dt>{t('product.category')}:</dt>
                  <dd><Link to={`/products?category=${product.category.slug}`}>{categoryName}</Link></dd>
                </div>
              )}
            </dl>

            <div className="pdp-perks">
              <div><Icon name="truck" size={22} /> {t('home.trustShipText', 'ارسال به سراسر کشور با پست و تیپاکس')}</div>
              <div><Icon name="returns" size={22} /> {t('home.trustReturnText', '۷ روز ضمانت بازگشت کالا')}</div>
              <div><Icon name="shield" size={22} /> {t('footer.genuine', 'ضمانت اصالت کالا')}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="pdp-details">
        <div className="container narrow-wide">
          <Accordion
            id="about"
            title={t('product.aboutProduct', 'درباره {{name}}', { name })}
            open={openSection.about}
            onToggle={() => setOpenSection((s) => ({ ...s, about: !s.about }))}
          >
            <p className="pdp-description">{description}</p>
          </Accordion>

          <Accordion
            id="specs"
            title={t('product.specifications')}
            open={openSection.specs}
            onToggle={() => setOpenSection((s) => ({ ...s, specs: !s.specs }))}
          >
            <dl className="spec-table">
              {specs.map((s) => (
                <div key={s.label}><dt>{s.label}</dt><dd>{s.value}</dd></div>
              ))}
            </dl>
          </Accordion>

          <Accordion
            id="reviews"
            title={`${t('product.customerReviews')} (${num(reviews.length)})`}
            open={openSection.reviews}
            onToggle={() => setOpenSection((s) => ({ ...s, reviews: !s.reviews }))}
          >
            {reviews.length > 0 ? (
              <>
                <div className="review-summary">
                  <strong>{num(avgRating.toFixed(1))}</strong>
                  <Stars value={avgRating} size={20} />
                  <span>{t('product.reviewsCount', { count: num(reviews.length) })}</span>
                </div>
                <ul className="review-list">
                  {reviews.map((review) => (
                    <li key={review.id} className="review-item">
                      <div className="review-head">
                        <strong>{review.user.display_name}</strong>
                        {review.is_verified_purchase && (
                          <span className="verified"><Icon name="check" size={14} /> {t('product.verifiedPurchase')}</span>
                        )}
                        <time dateTime={review.created_at}>
                          {formatDate(review.created_at, lang)}
                        </time>
                      </div>
                      <Stars value={review.rating} size={14} />
                      <h3>{review.title}</h3>
                      <p>{review.comment}</p>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <p className="muted">{t('product.noReviews')}</p>
            )}

            {isAuthenticated && !alreadyReviewed && (
              <form onSubmit={handleSubmitReview} className="review-form">
                <h3>{t('product.writeReview')}</h3>
                <div className="form-group">
                  <span className="form-label">{t('product.rating')}</span>
                  <div className="rating-input" role="radiogroup" aria-label={t('product.rating')}>
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        role="radio"
                        aria-checked={reviewForm.rating === star}
                        aria-label={num(star)}
                        onClick={() => setReviewForm({ ...reviewForm, rating: star })}
                        className={star <= reviewForm.rating ? 'on' : ''}
                      >
                        <Icon name="star" size={26} filled={star <= reviewForm.rating} strokeWidth={1.4} />
                      </button>
                    ))}
                  </div>
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="review-title">{t('product.title')}</label>
                  <input
                    id="review-title"
                    type="text"
                    value={reviewForm.title}
                    onChange={(e) => setReviewForm({ ...reviewForm, title: e.target.value })}
                    className="form-input"
                    maxLength={100}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="review-comment">{t('product.review')}</label>
                  <textarea
                    id="review-comment"
                    value={reviewForm.comment}
                    onChange={(e) => setReviewForm({ ...reviewForm, comment: e.target.value })}
                    className="form-textarea"
                    rows={4}
                    required
                  />
                </div>
                <button type="submit" disabled={submittingReview} className="btn btn-primary">
                  {submittingReview ? t('common.loading') : t('product.submitReview')}
                </button>
              </form>
            )}
            {!isAuthenticated && (
              <p className="muted">
                <Link to="/login">{t('product.loginToReview', 'برای ثبت نظر وارد شوید')}</Link>
              </p>
            )}
          </Accordion>
        </div>
      </div>

      {related.length > 0 && (
        <section className="band">
          <div className="container">
            <div className="section-head-center">
              <h2 className="section-title">{t('product.related', 'محصولات مشابه')}</h2>
            </div>
            <div className="product-grid">
              {related.map((p) => <ProductCard key={p.id} product={p} />)}
            </div>
          </div>
        </section>
      )}

      {product.in_stock && (
        <div className="pdp-sticky-bar">
          <div className="pdp-sticky-price">
            <Price amount={effective} />
          </div>
          <button onClick={handleAddToCart} disabled={addingToCart} className="btn btn-primary">
            {addingToCart ? t('common.loading') : t('common.addToCart')}
          </button>
        </div>
      )}

      {showSizeGuide && (
        <div className="modal-overlay" onClick={() => setShowSizeGuide(false)}>
          <div className="modal" role="dialog" aria-modal="true" aria-labelledby="size-guide-title" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 id="size-guide-title">{t('product.sizeGuide')}</h2>
              <button onClick={() => setShowSizeGuide(false)} className="icon-btn" aria-label={t('common.close', 'بستن')}>
                <Icon name="close" />
              </button>
            </div>
            <div className="modal-body">
              <p>{t('product.sizeGuideDesc')}</p>
              <table className="size-table">
                <thead>
                  <tr>
                    <th>{t('product.size')}</th>
                    <th>{t('product.measurement')}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr><td>S</td><td>{t('product.sizeS', '۳۰ تا ۳۵ سانتی‌متر')}</td></tr>
                  <tr><td>M</td><td>{t('product.sizeM', '۳۵ تا ۴۰ سانتی‌متر')}</td></tr>
                  <tr><td>L</td><td>{t('product.sizeL', '۴۰ تا ۴۵ سانتی‌متر')}</td></tr>
                  <tr><td>XL</td><td>{t('product.sizeXL', '۴۵ تا ۵۰ سانتی‌متر')}</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
