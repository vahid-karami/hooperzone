import { createContext, useCallback, useContext, useState, useEffect } from 'react';
import apiClient from '../api/client';
import { ENDPOINTS } from '../api/endpoints';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const tokens = JSON.parse(localStorage.getItem('tokens') || '{}');
    const savedUser = localStorage.getItem('user');
    if (tokens.access && savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const sendOTP = async (phone, otpType = 'register') => {
    const response = await apiClient.post(ENDPOINTS.sendOTP, { phone, otp_type: otpType });
    return response.data;
  };

  const verifyOTP = async (phone, code, otpType = 'register') => {
    const response = await apiClient.post(ENDPOINTS.verifyOTP, {
      phone,
      code,
      otp_type: otpType,
    });
    if (response.data.tokens) {
      localStorage.setItem('tokens', JSON.stringify(response.data.tokens));
      localStorage.setItem('user', JSON.stringify(response.data.user));
      setUser(response.data.user);
    }
    return response.data;
  };

  const register = async (userData) => {
    const response = await apiClient.post(ENDPOINTS.register, userData);
    if (response.data.tokens) {
      localStorage.setItem('tokens', JSON.stringify(response.data.tokens));
      localStorage.setItem('user', JSON.stringify(response.data.user));
      setUser(response.data.user);
    }
    return response.data;
  };

  const loginWithPassword = async (identifier, password) => {
    const response = await apiClient.post(ENDPOINTS.loginPassword, {
      username: identifier,
      phone: identifier,
      password,
    });
    if (response.data.tokens) {
      localStorage.setItem('tokens', JSON.stringify(response.data.tokens));
      localStorage.setItem('user', JSON.stringify(response.data.user));
      setUser(response.data.user);
    }
    return response.data;
  };

  const resetPassword = async (phone, code, newPassword) => {
    const response = await apiClient.post(ENDPOINTS.resetPassword, {
      phone,
      code,
      new_password: newPassword,
    });
    return response.data;
  };

  const logout = () => {
    localStorage.removeItem('tokens');
    localStorage.removeItem('user');
    setUser(null);
  };

  const updateProfile = async (data) => {
    const response = await apiClient.patch(ENDPOINTS.profile, data);
    localStorage.setItem('user', JSON.stringify(response.data));
    setUser(response.data);
    return response.data;
  };

  // Re-read the profile, e.g. after the owner changed this user's staff access.
  const refreshUser = useCallback(async () => {
    const response = await apiClient.get(ENDPOINTS.profile);
    localStorage.setItem('user', JSON.stringify(response.data));
    setUser(response.data);
    return response.data;
  }, []);

  const isAuthenticated = !!user;

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated,
        sendOTP,
        verifyOTP,
        register,
        loginWithPassword,
        resetPassword,
        logout,
        updateProfile,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
