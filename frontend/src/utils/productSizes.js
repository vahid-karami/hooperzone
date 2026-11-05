import { toEnglishDigits } from './digits';

// Admin form rows keep stock as typed text; the API takes numbers.
export const sizesFromProduct = (p) =>
  (p.sizes || []).map((s) => ({ id: s.id, label: s.label, stock: String(s.stock), sku: s.sku || '', is_active: s.is_active }));

export const sizesPayload = (rows) =>
  rows
    .filter((r) => r.label.trim())
    .map((r, i) => ({
      ...(r.id ? { id: r.id } : {}),
      label: r.label.trim(),
      stock: parseInt(toEnglishDigits(r.stock), 10) || 0,
      sku: r.sku.trim(),
      is_active: r.is_active,
      sort_order: i,
    }));

export const sizesTotal = (rows) =>
  rows.filter((r) => r.is_active && r.label.trim()).reduce((sum, r) => sum + (parseInt(toEnglishDigits(r.stock), 10) || 0), 0);
