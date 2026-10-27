import { useEffect, Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { AuthProvider, CartProvider, FavoritesProvider } from './context';
import Header from './components/Header';
import Footer from './components/Footer';
import { PageLoader, ScrollToTop, usePrefetchPages } from './components/RouteHelpers';
import ToastContainer from './components/ToastContainer';
import { ToastProvider } from './context/ToastContext';

const loadProducts = () => import('./pages/Products');
const loadProductDetail = () => import('./pages/ProductDetail');
const loadCart = () => import('./pages/Cart');

const Home = lazy(() => import('./pages/Home'));
const Products = lazy(loadProducts);
const ProductDetail = lazy(loadProductDetail);
const Categories = lazy(() => import('./pages/Categories'));
const Cart = lazy(loadCart);
const Checkout = lazy(() => import('./pages/Checkout'));
const Login = lazy(() => import('./pages/Login'));
const Register = lazy(() => import('./pages/Register'));
const Profile = lazy(() => import('./pages/Profile'));
const Orders = lazy(() => import('./pages/Orders'));
const OrderDetail = lazy(() => import('./pages/OrderDetail'));
const Favorites = lazy(() => import('./pages/Favorites'));
const PaymentResult = lazy(() => import('./pages/PaymentResult'));
const InfoPage = lazy(() => import('./pages/info/InfoPage'));
const NotFound = lazy(() => import('./pages/NotFound'));
const AdminLayout = lazy(() => import('./layouts/AdminLayout'));
const AdminDashboard = lazy(() => import('./pages/admin/AdminDashboard'));
const AdminProducts = lazy(() => import('./pages/admin/AdminProducts'));
const AdminCategories = lazy(() => import('./pages/admin/AdminCategories'));
const AdminPriceDeclaration = lazy(() => import('./pages/admin/AdminPriceDeclaration'));
const AdminOrders = lazy(() => import('./pages/admin/AdminOrders'));
const AdminInvoice = lazy(() => import('./pages/admin/AdminInvoice'));
const AdminCustomers = lazy(() => import('./pages/admin/AdminCustomers'));
const AdminSettings = lazy(() => import('./pages/admin/AdminSettings'));

function AppRoutes() {
  const location = useLocation();
  // Re-keying on the page path replays the fade-in; the admin portal keeps its sidebar mounted.
  const viewKey = location.pathname.startsWith('/admin-portal') ? 'admin' : location.pathname;

  return (
    <div key={viewKey} className="route-view">
      <Routes location={location}>
        <Route path="/" element={<Home />} />
        <Route path="/products" element={<Products />} />
        <Route path="/products/:slug" element={<ProductDetail />} />
        <Route path="/categories" element={<Categories />} />
        <Route path="/cart" element={<Cart />} />
        <Route path="/checkout" element={<Checkout />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/profile" element={<Profile />} />
        <Route path="/orders" element={<Orders />} />
        <Route path="/orders/:orderNumber" element={<OrderDetail />} />
        <Route path="/payment/result" element={<PaymentResult />} />
        <Route path="/favorites" element={<Favorites />} />
        {['about', 'contact', 'faq', 'shipping', 'returns', 'terms', 'privacy'].map((page) => (
          <Route key={page} path={`/${page}`} element={<InfoPage page={page} />} />
        ))}

        <Route path="/admin-portal" element={<AdminLayout />}>
          <Route index element={<AdminDashboard />} />
          <Route path="orders" element={<AdminOrders />} />
          <Route path="orders/:orderNumber/invoice" element={<AdminInvoice />} />
          <Route path="customers" element={<AdminCustomers />} />
          <Route path="settings" element={<AdminSettings />} />
          <Route path="products" element={<AdminProducts />} />
          <Route path="categories" element={<AdminCategories />} />
          <Route path="price-declaration" element={<AdminPriceDeclaration />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </div>
  );
}

function App() {
  const { i18n } = useTranslation();
  usePrefetchPages([loadProducts, loadProductDetail, loadCart]);

  useEffect(() => {
    const dir = i18n.language === 'fa' ? 'rtl' : 'ltr';
    document.documentElement.setAttribute('dir', dir);
    document.documentElement.setAttribute('lang', i18n.language);
  }, [i18n.language]);

  return (
    <Router>
      <ToastProvider>
        <AuthProvider>
          <CartProvider>
            <FavoritesProvider>
              <ScrollToTop />
              <div className="app">
                <Header />
                <main>
                  <Suspense fallback={<PageLoader />}>
                    <AppRoutes />
                  </Suspense>
                </main>
                <Footer />
              </div>
              <ToastContainer />
            </FavoritesProvider>
          </CartProvider>
        </AuthProvider>
      </ToastProvider>
    </Router>
  );
}

export default App;
