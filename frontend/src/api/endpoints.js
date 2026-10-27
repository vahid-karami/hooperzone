export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

// Django's own admin (image uploads etc.). In dev it lives on the Django server, not behind Vite.
export const DJANGO_ADMIN_URL = import.meta.env.DEV
  ? `${import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'}/admin/`
  : '/admin/';

export const ENDPOINTS = {
  sendOTP: `${API_BASE_URL}/auth/otp/send/`,
  verifyOTP: `${API_BASE_URL}/auth/otp/verify/`,
  register: `${API_BASE_URL}/auth/register/`,
  resetPassword: `${API_BASE_URL}/auth/password/reset/`,
  loginPassword: `${API_BASE_URL}/auth/login/`,
  profile: `${API_BASE_URL}/auth/profile/`,
  tokenRefresh: `${API_BASE_URL}/token/refresh/`,

  categories: `${API_BASE_URL}/products/categories/`,
  sports: `${API_BASE_URL}/products/sports/`,
  products: `${API_BASE_URL}/products/`,
  productDetail: (slug) => `${API_BASE_URL}/products/${slug}/`,
  featuredProducts: `${API_BASE_URL}/products/featured/`,
  injuryTypes: `${API_BASE_URL}/products/injury_types/`,
  
  adminProducts: `${API_BASE_URL}/products/admin/products/`,
  adminProductDetail: (slug) => `${API_BASE_URL}/products/admin/products/${slug}/`,
  adminBulkPriceUpdate: `${API_BASE_URL}/products/admin/products/bulk_price_update/`,

  cart: `${API_BASE_URL}/cart/`,
  cartAdd: `${API_BASE_URL}/cart/add/`,
  cartUpdate: `${API_BASE_URL}/cart/update/`,
  cartRemove: `${API_BASE_URL}/cart/remove/`,
  cartClear: `${API_BASE_URL}/cart/clear/`,

  orders: `${API_BASE_URL}/orders/`,
  orderCreate: `${API_BASE_URL}/orders/create/`,
  orderDetail: (id) => `${API_BASE_URL}/orders/${id}/`,
  orderCancel: (id) => `${API_BASE_URL}/orders/${id}/cancel/`,
  orderPay: (id) => `${API_BASE_URL}/orders/${id}/pay/`,
  paymentVerify: `${API_BASE_URL}/orders/payment/verify/`,
  shippingMethods: `${API_BASE_URL}/orders/shipping-methods/`,
  shopInfo: `${API_BASE_URL}/orders/shop-info/`,
  adminStats: `${API_BASE_URL}/orders/admin/stats/`,
  adminOrders: `${API_BASE_URL}/orders/admin/`,
  adminOrderUpdate: (id) => `${API_BASE_URL}/orders/admin/${id}/`,

  productReviews: (slug) => `${API_BASE_URL}/reviews/product/${slug}/`,
  reviewCreate: (slug) => `${API_BASE_URL}/reviews/product/${slug}/create/`,
  reviewUpdate: (id) => `${API_BASE_URL}/reviews/${id}/update/`,
  reviewDelete: (id) => `${API_BASE_URL}/reviews/${id}/delete/`,

  favorites: `${API_BASE_URL}/favorites/`,
  favoriteAdd: `${API_BASE_URL}/favorites/add/`,
  favoriteRemove: `${API_BASE_URL}/favorites/remove/`,
  favoriteClear: `${API_BASE_URL}/favorites/clear/`,
};
