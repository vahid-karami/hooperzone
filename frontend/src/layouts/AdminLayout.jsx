import { Link, NavLink, Outlet, Navigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { DJANGO_ADMIN_URL } from '../api/endpoints';
import Icon from '../components/Icon';
import LoadingSpinner from '../components/LoadingSpinner';

export default function AdminLayout() {
  const { t } = useTranslation();
  const { user, isAuthenticated, loading } = useAuth();

  if (loading) return <LoadingSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  // The API enforces staff permissions too; this just keeps customers out of the UI.
  if (!user?.is_staff) {
    return (
      <div className="container">
        <div className="empty-panel">
          <Icon name="shield" size={44} strokeWidth={1.4} />
          <h2>{t('admin.noAccess', 'دسترسی به پنل مدیریت ندارید')}</h2>
          <p>{t('admin.noAccessText', 'این بخش فقط برای کارکنان فروشگاه است.')}</p>
          <Link to="/" className="btn btn-primary">{t('common.home')}</Link>
        </div>
      </div>
    );
  }

  const items = [
    { to: '/admin-portal', end: true, icon: 'chart', label: t('admin.dashboard', 'داشبورد') },
    { to: '/admin-portal/orders', icon: 'box', label: t('admin.orders', 'سفارش‌ها') },
    { to: '/admin-portal/products', icon: 'bag', label: t('admin.products', 'محصولات') },
    { to: '/admin-portal/categories', icon: 'menu', label: t('admin.categories', 'دسته‌بندی‌ها') },
    { to: '/admin-portal/customers', icon: 'users', label: t('admin.customersTitle', 'مشتریان') },
    { to: '/admin-portal/price-declaration', icon: 'card', label: t('admin.priceList', 'اعلامیه قیمت') },
    { to: '/admin-portal/settings', icon: 'settings', label: t('admin.settings', 'تنظیمات فروشگاه') },
  ];

  return (
    <div className="admin-shell">
      <aside className="admin-side">
        <div className="admin-side-head">
          <span className="admin-side-title">{t('admin.title', 'پنل مدیریت')}</span>
          <span className="admin-side-user">{user.first_name || user.username || user.phone}</span>
        </div>
        <nav className="admin-side-nav" aria-label={t('admin.title', 'پنل مدیریت')}>
          {items.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => `admin-link ${isActive ? 'active' : ''}`}>
              <Icon name={item.icon} size={20} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="admin-side-foot">
          <a href={DJANGO_ADMIN_URL} target="_blank" rel="noreferrer" className="admin-link subtle">
            <Icon name="shield" size={18} />
            <span>{t('admin.djangoAdvanced', 'مدیریت پیشرفته (جنگو)')}</span>
          </a>
          <Link to="/" className="admin-link subtle">
            <Icon name="arrowLeft" size={18} className="flip-ltr" />
            <span>{t('admin.backToShop', 'بازگشت به فروشگاه')}</span>
          </Link>
        </div>
      </aside>
      <main className="admin-content">
        <Outlet />
      </main>
    </div>
  );
}
