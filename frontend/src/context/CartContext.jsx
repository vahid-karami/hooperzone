import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import apiClient from '../api/client';
import { ENDPOINTS } from '../api/endpoints';
import { useAuth } from './AuthContext';

const CartContext = createContext(null);

export function CartProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [cart, setCart] = useState({ items: [], total_price: 0, total_items: 0 });
  const [loading, setLoading] = useState(false);

  const fetchCart = useCallback(async () => {
    if (!isAuthenticated) {
      setCart({ items: [], total_price: 0, total_items: 0 });
      return;
    }
    setLoading(true);
    try {
      const response = await apiClient.get(ENDPOINTS.cart);
      setCart(response.data);
    } catch (error) {
      console.error('Failed to fetch cart:', error);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    fetchCart();
  }, [fetchCart]);

  // sizeId is required for products that have sizes (product.sizes / product.size_labels).
  const addToCart = async (productId, quantity = 1, sizeId = null) => {
    const response = await apiClient.post(ENDPOINTS.cartAdd, {
      product_id: productId,
      quantity,
      ...(sizeId ? { size_id: sizeId } : {}),
    });
    setCart(response.data);
    return response.data;
  };

  const updateCartItem = async (itemId, quantity) => {
    const response = await apiClient.patch(ENDPOINTS.cartUpdate, {
      item_id: itemId,
      quantity,
    });
    setCart(response.data);
    return response.data;
  };

  const removeFromCart = async (itemId) => {
    const response = await apiClient.delete(ENDPOINTS.cartRemove, {
      data: { item_id: itemId },
    });
    setCart(response.data);
    return response.data;
  };

  const clearCart = async () => {
    const response = await apiClient.delete(ENDPOINTS.cartClear);
    setCart(response.data);
    return response.data;
  };

  return (
    <CartContext.Provider
      value={{
        cart,
        loading,
        addToCart,
        updateCartItem,
        removeFromCart,
        clearCart,
        refreshCart: fetchCart,
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export const useCart = () => {
  const context = useContext(CartContext);
  if (!context) {
    throw new Error('useCart must be used within a CartProvider');
  }
  return context;
};
