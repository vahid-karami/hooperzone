import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { useCart } from '../context/CartContext';
import { useFavorites } from '../context/FavoritesContext';
import { BODY_PARTS } from '../utils/bodyParts';
import { useShopInfo, baleHref } from '../utils/shopInfo';
import { useCategories, useSports, sportName } from '../utils/catalog';
import Icon from './Icon';
import Logo from './Logo';

export default function Header() {
  const { t, i18n } = useTranslation();
  const lang = i18n.language === 'fa' ? 'fa' : 'en';
  const { isAuthenticated, logout, user } = useAuth();
  const { cart } = useCart();
  const { favorites } = useFavorites();
  const navigate = useNavigate();
  const location = useLocation();

  const categories = useCategories();
  const sports = useSports();
  const [megaOpen, setMegaOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [accountOpen, setAccountOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const headerRef = useRef(null);
  const toolsRef = useRef(null);
  const shop = useShopInfo();
  const baleLink = baleHref(shop.bale);

  // Close every overlay on navigation.
  const onSalePage = new URLSearchParams(location.search).get('on_sale') === 'true';
  const routeKey = location.pathname + location.search;
  const [lastRouteKey, setLastRouteKey] = useState(routeKey);
  if (routeKey !== lastRouteKey) {
    setLastRouteKey(routeKey);
    setMegaOpen(false);
    setDrawerOpen(false);
    setAccountOpen(false);
  }

  // On phones the header is tall (logo row, search box, labelled shortcuts), so only the
  // shortcut row stays pinned while scrolling: the header sticks at minus the height above it.
  useEffect(() => {
    const header = headerRef.current;
    const tools = toolsRef.current;
    if (!header || !tools || !('ResizeObserver' in window)) return undefined;
    const update = () => {
      const offset = tools.getBoundingClientRect().top - header.getBoundingClientRect().top;
      header.style.setProperty('--header-stick', `${-Math.round(offset)}px`);
    };
    const ro = new ResizeObserver(update);
    ro.observe(header);
    update();
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    document.body.style.overflow = drawerOpen ? 'hidden' : '';
    if (!drawerOpen) return undefined;
    const onKey = (e) => e.key === 'Escape' && setDrawerOpen(false);
    document.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', onKey);
    };
  }, [drawerOpen]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    const q = searchQuery.trim();
    if (q) navigate(`/products?search=${encodeURIComponent(q)}`);
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const catName = (c) => (lang === 'fa' ? c.name_fa || c.name : c.name);
  const partName = (p) => (lang === 'fa' ? p.fa : p.en);

  return (
    <header className="site-header" ref={headerRef}>
      <div className="announcement-bar">
        <div className="container announcement-inner">
          <div className="announcement-account">
            {isAuthenticated ? (
              <Link to="/profile">
                {t('header.hello', 'سلام')}، {user?.first_name || user?.username || user?.phone}
              </Link>
            ) : (
              <Link to="/login">{t('header.loginOrSignup', 'ورود یا ثبت‌نام')}</Link>
            )}
          </div>
          <p className="announcement-text">
            {t('header.announcement', 'ارسال به سراسر ایران با پست و تیپاکس · ۷ روز ضمانت بازگشت کالا')}
          </p>
          <div className="announcement-spacer" />
        </div>
      </div>

      <div className="header-bar">
        <div className="container header-grid">
          <nav className="primary-nav" aria-label={t('header.mainNav', 'منوی اصلی')}>
            <button
              className="icon-btn drawer-toggle"
              onClick={() => setDrawerOpen(true)}
              aria-label={t('header.openMenu', 'باز کردن منو')}
            >
              <Icon name="menu" />
            </button>

            <div
              className={`nav-item has-mega ${megaOpen ? 'open' : ''}`}
              onMouseEnter={() => setMegaOpen(true)}
              onMouseLeave={() => setMegaOpen(false)}
            >
              <button className="nav-link" aria-expanded={megaOpen} onClick={() => setMegaOpen((o) => !o)}>
                {t('common.shop')}
                <Icon name="chevronDown" size={16} />
              </button>
              <div className="mega-menu">
                <div className="container mega-grid">
                  <div className="mega-col">
                    <h4 className="mega-title">{t('home.shopByBodyPart')}</h4>
                    <ul className="mega-links two-col">
                      {BODY_PARTS.map((p) => (
                        <li key={p.key}>
                          <Link to={`/products?injury_type=${p.key}`}>{partName(p)}</Link>
                        </li>
                      ))}
                    </ul>
                  </div>
                  {sports.length > 0 && (
                    <div className="mega-col">
                      <h4 className="mega-title">{t('home.shopBySport', 'خرید بر اساس ورزش')}</h4>
                      <ul className="mega-links">
                        {sports.map((s) => (
                          <li key={s.slug}>
                            <Link to={`/products?sport=${s.slug}`}>{sportName(s, lang)}</Link>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <div className="mega-col">
                    <h4 className="mega-title">{t('header.productTypes', 'دسته‌بندی محصولات')}</h4>
                    <ul className="mega-links">
                      {categories.map((c) => (
                        <li key={c.id}>
                          <Link to={`/products?category=${c.slug}`}>{catName(c)}</Link>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div className="mega-col">
                    <h4 className="mega-title">{t('header.quickLinks', 'دسترسی سریع')}</h4>
                    <ul className="mega-links">
                      <li><Link to="/products?on_sale=true">{t('header.offers', 'تخفیف‌ها')}</Link></li>
                      <li><Link to="/products?ordering=-created_at">{t('products.newest')}</Link></li>
                      <li><Link to="/products">{t('products.allProducts')}</Link></li>
                    </ul>
                  </div>
                  <Link to="/products?on_sale=true" className="mega-promo">
                    <span className="eyebrow">{t('header.offers', 'تخفیف‌ها')}</span>
                    <strong>{t('header.megaPromoTitle', 'پیشنهادهای ویژه این هفته')}</strong>
                    <span className="link-arrow">
                      {t('home.seeOffers', 'مشاهده پیشنهادها')} <Icon name="arrowLeft" size={16} />
                    </span>
                  </Link>
                </div>
              </div>
            </div>

            <Link
              to="/products?on_sale=true"
              className={`nav-link hide-md ${location.pathname === '/products' && onSalePage ? 'active' : ''}`}
            >
              {t('header.offers', 'تخفیف‌ها')}
            </Link>
            <Link to="/categories" className={`nav-link hide-md ${location.pathname === '/categories' ? 'active' : ''}`}>
              {t('header.categories')}
            </Link>
          </nav>

          <div className="header-logo">
            <Logo />
          </div>

          <form className="header-search" onSubmit={handleSearchSubmit} role="search">
            <Icon name="search" size={22} />
            <input
              type="search"
              enterKeyHint="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('header.searchPlaceholder', 'دنبال چه محصولی هستید؟ مثلاً زانوبند')}
              aria-label={t('common.search')}
            />
            <button type="submit" className="btn btn-primary">
              {t('common.search')}
            </button>
          </form>

          <div className="header-tools" ref={toolsRef}>
            <Link to="/products" className="tool tool-mobile">
              <span className="tool-icon"><Icon name="store" /></span>
              <span className="tool-label">{t('header.shop', 'فروشگاه')}</span>
            </Link>

            {baleLink && (
              <a href={baleLink} target="_blank" rel="noreferrer" className="tool tool-bale">
                <span className="tool-icon"><Icon name="chat" /></span>
                <span className="tool-label">{t('header.bale', 'پیام در بله')}</span>
              </a>
            )}

            <Link to="/favorites" className="tool hide-sm">
              <span className="tool-icon">
                <Icon name="heart" />
                {favorites.total_items > 0 && <span className="count-badge">{favorites.total_items}</span>}
              </span>
              <span className="tool-label">{t('header.favoritesShort', 'علاقه‌مندی')}</span>
            </Link>

            {isAuthenticated ? (
              <div className={`account-menu ${accountOpen ? 'open' : ''}`}>
                <button
                  className={`tool ${accountOpen ? 'active' : ''}`}
                  onClick={() => setAccountOpen((o) => !o)}
                  aria-expanded={accountOpen}
                >
                  <span className="tool-icon"><Icon name="user" /></span>
                  <span className="tool-label">{t('header.myAccount')}</span>
                </button>
                <div className="account-dropdown">
                  <Link to="/profile">{t('header.myAccount')}</Link>
                  <Link to="/orders">{t('header.myOrders')}</Link>
                  <Link to="/favorites">{t('header.myFavorites')}</Link>
                  {user?.is_staff && <Link to="/admin-portal">{t('header.adminPanel', 'پنل مدیریت')}</Link>}
                  <button onClick={handleLogout} className="danger">
                    <Icon name="logout" size={18} /> {t('common.logout')}
                  </button>
                </div>
              </div>
            ) : (
              <Link to="/login" className="tool">
                <span className="tool-icon"><Icon name="user" /></span>
                <span className="tool-label">{t('header.loginShort', 'ورود / ثبت‌نام')}</span>
              </Link>
            )}

            <Link to="/cart" className="tool">
              <span className="tool-icon">
                <Icon name="bag" />
                {cart.total_items > 0 && <span className="count-badge">{cart.total_items}</span>}
              </span>
              <span className="tool-label">{t('common.cart')}</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Mobile drawer */}
      <div className={`drawer-backdrop ${drawerOpen ? 'open' : ''}`} onClick={() => setDrawerOpen(false)} />
      <aside className={`drawer ${drawerOpen ? 'open' : ''}`} aria-hidden={!drawerOpen} inert={!drawerOpen}>
        <div className="drawer-head">
          <Logo />
          <button className="icon-btn" onClick={() => setDrawerOpen(false)} aria-label={t('header.closeMenu', 'بستن منو')}>
            <Icon name="close" />
          </button>
        </div>
        <div className="drawer-body">
          <p className="drawer-title">{t('home.shopByBodyPart')}</p>
          <div className="drawer-chips">
            {BODY_PARTS.map((p) => (
              <Link key={p.key} to={`/products?injury_type=${p.key}`} className="chip">
                {partName(p)}
              </Link>
            ))}
          </div>
          {sports.length > 0 && (
            <>
              <p className="drawer-title">{t('home.shopBySport', 'خرید بر اساس ورزش')}</p>
              <div className="drawer-chips">
                {sports.map((s) => (
                  <Link key={s.slug} to={`/products?sport=${s.slug}`} className="chip">
                    {sportName(s, lang)}
                  </Link>
                ))}
              </div>
            </>
          )}
          <p className="drawer-title">{t('header.productTypes', 'دسته‌بندی محصولات')}</p>
          <ul className="drawer-links">
            {categories.map((c) => (
              <li key={c.id}>
                <Link to={`/products?category=${c.slug}`}>
                  {catName(c)} <Icon name="chevronLeft" size={16} />
                </Link>
              </li>
            ))}
            <li>
              <Link to="/products?on_sale=true">
                {t('header.offers', 'تخفیف‌ها')} <Icon name="chevronLeft" size={16} />
              </Link>
            </li>
            <li>
              <Link to="/products">
                {t('products.allProducts')} <Icon name="chevronLeft" size={16} />
              </Link>
            </li>
          </ul>
          <p className="drawer-title">{t('header.myAccount')}</p>
          <ul className="drawer-links">
            {isAuthenticated ? (
              <>
                <li><Link to="/profile">{t('header.myAccount')}</Link></li>
                <li><Link to="/orders">{t('header.myOrders')}</Link></li>
                <li><Link to="/favorites">{t('header.myFavorites')}</Link></li>
                <li><button onClick={handleLogout} className="danger">{t('common.logout')}</button></li>
              </>
            ) : (
              <>
                <li><Link to="/login">{t('common.login')}</Link></li>
                <li><Link to="/register">{t('common.register')}</Link></li>
              </>
            )}
          </ul>
        </div>
      </aside>
    </header>
  );
}
