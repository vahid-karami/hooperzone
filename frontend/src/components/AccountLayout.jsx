import { Link, NavLink, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import Breadcrumbs from './Breadcrumbs';
import Icon from './Icon';
import LoadingSpinner from './LoadingSpinner';
import { loginState } from '../utils/authRedirect';
import { toPersianNumber } from '../hooks/useLanguage';

// "My account" shell: side navigation + page content. Redirects guests to login.
export default function AccountLayout({ title, actions, children }) {
  const { t, i18n } = useTranslation();
  const { user, isAuthenticated, loading, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  if (loading) return <LoadingSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" replace state={loginState(location)} />;

  const phone = user?.phone && i18n.language === 'fa' ? toPersianNumber(user.phone) : user?.phone;
  const displayName = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || phone;
  const initial = (user?.first_name || user?.username || '؟').trim().charAt(0).toUpperCase();

  const links = [
    { to: '/profile', icon: 'user', label: t('header.myAccount') },
    { to: '/orders', icon: 'box', label: t('header.myOrders') },
    { to: '/favorites', icon: 'heart', label: t('header.myFavorites') },
    { to: '/cart', icon: 'bag', label: t('common.cart') },
  ];

  return (
    <div className="account-page">
      <div className="container">
        <Breadcrumbs items={[{ to: '/', label: t('common.home') }, { label: title }]} />
        <div className="account-layout">
          <aside className="account-nav">
            <div className="account-user">
              <span className="account-avatar" aria-hidden="true">{initial}</span>
              <div>
                <strong>{displayName}</strong>
                {phone && <span dir="ltr">{phone}</span>}
              </div>
            </div>
            <nav aria-label={t('header.myAccount')}>
              {links.map((l) => (
                <NavLink key={l.to} to={l.to} end className={({ isActive }) => `account-link ${isActive ? 'active' : ''}`}>
                  <Icon name={l.icon} size={20} /> {l.label}
                </NavLink>
              ))}
              {user?.is_staff && (
                <Link to="/admin-portal" className="account-link">
                  <Icon name="shield" size={20} /> {t('header.adminPanel', 'پنل مدیریت')}
                </Link>
              )}
              <button
                type="button"
                className="account-link danger"
                onClick={() => {
                  logout();
                  navigate('/');
                }}
              >
                <Icon name="logout" size={20} /> {t('common.logout')}
              </button>
            </nav>
          </aside>

          <section className="account-main">
            <div className="account-head">
              <h1 className="display-title">{title}</h1>
              {actions}
            </div>
            {children}
          </section>
        </div>
      </div>
    </div>
  );
}
