import { useEffect, useState } from 'react';
import apiClient from '../api/client';
import { ENDPOINTS } from '../api/endpoints';

// Store contact details and shipping fees (edited in the admin portal). Fetched once per page load.
let cache = null;
let pending = null;

export function loadShopInfo() {
  if (cache) return Promise.resolve(cache);
  if (!pending) {
    pending = apiClient
      .get(ENDPOINTS.shopInfo)
      .then((res) => {
        cache = res.data;
        return cache;
      })
      .catch(() => {
        pending = null;
        return {};
      });
  }
  return pending;
}

export function useShopInfo() {
  const [info, setInfo] = useState(cache || {});
  useEffect(() => {
    let active = true;
    loadShopInfo().then((data) => active && setInfo(data));
    return () => {
      active = false;
    };
  }, []);
  return info;
}

// "+98 21 ..." style tel: link from whatever the staff typed.
export const telHref = (phone) => `tel:${String(phone || '').replace(/[^\d+]/g, '')}`;
